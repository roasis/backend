import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from xrpl.asyncio.transaction import XRPLReliableSubmissionException
from xrpl.clients import JsonRpcClient
from xrpl.models.requests import AccountInfo, AccountObjects, Tx
from xrpl.models.transactions import NFTokenMint, TicketCreate, NFTokenCreateOffer
from xrpl.transaction import autofill, sign, submit_and_wait
from xrpl.utils import str_to_hex
from xrpl.wallet import Wallet
from functools import partial

from app.core.config import settings
from app.shared.pinata_client import pin_file_to_ipfs, pin_json_to_ipfs

from .models import NFT, Artwork

DEVNET_URL = "https://s.devnet.rippletest.net:51234/"


def _xrpl_client() -> JsonRpcClient:
    rpc = getattr(settings, "xrpl_rpc_url", DEVNET_URL) or DEVNET_URL
    return JsonRpcClient(rpc)


def _assert_funded(client: JsonRpcClient, address: str) -> int:
    req = AccountInfo(account=address, ledger_index="validated", strict=True)
    resp = client.request(req)
    if "account_data" not in resp.result:
        raise RuntimeError(f"account_info failed: {resp.result}")
    return int(resp.result["account_data"]["Sequence"])


def _get_ticket_sequences(client: JsonRpcClient, address: str, want: int) -> List[int]:
    req = AccountObjects(account=address, type="ticket")
    resp = client.request(req)
    objs = resp.result.get("account_objects", [])
    tickets = [int(o["TicketSequence"]) for o in objs]
    tickets.sort()
    return tickets[:want]


def _extract_minted_id(tx_result: Dict[str, Any]) -> Optional[str]:
    nft_id = tx_result.get("meta", {}).get("nftoken_id")
    if nft_id:
        return nft_id
    meta = tx_result.get("meta") or {}
    nodes = meta.get("AffectedNodes") or []
    for n in nodes:
        created = n.get("CreatedNode") or {}
        if created.get("LedgerEntryType") == "NFToken":
            fields = created.get("NewFields") or {}
            if "NFTokenID" in fields:
                return fields["NFTokenID"]
    return None


def _build_part_uri(base: str, idx: int, total: int) -> str:
    return f"{base}?p={idx}&t={total}"


def _extract_offer_index(tx_result: Dict[str, Any]) -> Optional[str]:
    meta = tx_result.get("meta") or {}
    nodes = meta.get("AffectedNodes") or []
    for n in nodes:
        created = n.get("CreatedNode") or {}
        if created.get("LedgerEntryType") == "NFTokenOffer":
            lid = created.get("LedgerIndex")
            if lid:
                return lid
            nf = created.get("NewFields") or {}
            if "index" in nf:
                return nf["index"]
    return None


def _create_nft_offer(
    client: JsonRpcClient,
    wallet: Wallet,
    nftoken_id: str,
    destination: str,
    price_drops: str,
) -> Dict[str, Any]:
    logging.info(f"Creating NFT offer: nftoken_id={nftoken_id}, destination={destination}, price={price_drops} drops")

    offer_tx = NFTokenCreateOffer(
        account=wallet.classic_address,
        nftoken_id=nftoken_id,
        amount=price_drops,       # 실제 가격 (drops)
        destination=destination,  # 작가 지갑 주소
        flags=1,                  # tfSellNFToken
    )

    logging.info(f"Offer transaction created: {offer_tx}")

    try:
        o_autofilled = autofill(offer_tx, client)
        logging.info(f"Offer transaction autofilled: {o_autofilled}")

        o_signed = sign(o_autofilled, wallet)
        logging.info("Offer transaction signed successfully")

        o_resp = submit_and_wait(o_signed, client)
        logging.info(f"Offer submission response: success={o_resp.is_successful()}")
        logging.info(f"FULL OFFER RESPONSE: {o_resp.result}")

        if not o_resp.is_successful():
            logging.error(f"Offer transaction failed: {o_resp.result}")

        return o_resp.result
    except Exception as e:
        logging.error(f"Error in offer creation process: {str(e)}")
        raise


def _sync_xrpl_batch_mint(
    db: Session,
    artwork_id: int,
    metadata_uri_base: str,
    grid_total: int,
    flags: int,
    transfer_fee: int,
    taxon: int,
    nft_price_usd: int,
) -> Dict[str, Any]:
    """동기 버전의 XRPL 배치 민팅 함수"""
    client = _xrpl_client()
    seed = settings.platform_seed
    if not seed:
        raise RuntimeError("platform_seed is not configured")
    wallet = Wallet.from_seed(seed)
    classic = wallet.classic_address

    current_seq = _assert_funded(client, classic)
    tc = TicketCreate(account=classic, ticket_count=grid_total, sequence=current_seq)
    tc_autofilled = autofill(tc, client)
    tc_signed = sign(tc_autofilled, wallet)
    tc_resp = submit_and_wait(tc_signed, client)
    if not tc_resp.is_successful():
        raise RuntimeError(f"TicketCreate failed: {tc_resp.result}")

    # 티켓 조회(지연 보정)
    time.sleep(0.5)
    tickets = _get_ticket_sequences(client, classic, grid_total)
    if len(tickets) < grid_total:
        time.sleep(1.0)
        tickets = _get_ticket_sequences(client, classic, grid_total)
    if len(tickets) < grid_total:
        raise RuntimeError(f"Not enough tickets: want={grid_total}, got={len(tickets)}")

    minted = 0
    tx_hashes: List[str] = []
    nft_ids: List[Optional[str]] = []
    errors: List[Any] = []

    for i, tseq in enumerate(tickets[:grid_total], start=1):
        part_uri = _build_part_uri(metadata_uri_base, i, grid_total)
        uri_hex = str_to_hex(part_uri)

        mint_tx = NFTokenMint(
            account=classic,
            uri=uri_hex,
            flags=int(flags),
            transfer_fee=int(transfer_fee),
            ticket_sequence=int(tseq),
            sequence=0,
            nftoken_taxon=int(taxon),
        )
        try:
            m_autofilled = autofill(mint_tx, client)
            m_signed = sign(m_autofilled, wallet)
            m_resp = submit_and_wait(m_signed, client)

            if m_resp.is_successful():
                minted += 1
                txh = m_resp.result.get("hash")
                nid = _extract_minted_id(m_resp.result)
                tx_hashes.append(txh)
                nft_ids.append(nid)

                db.add(
                    NFT(
                        artwork_id=artwork_id,
                        uri_hex=uri_hex,
                        nftoken_id=nid,
                        tx_hash=txh,
                        owner_address=classic,
                        status="minted",
                        price=nft_price_usd,
                        extra={
                            "part_uri": part_uri,
                            "grid_index": i,
                            "grid_total": grid_total,
                        },
                    )
                )
                db.commit()
            else:
                errors.append(m_resp.result)

        except XRPLReliableSubmissionException as e:
            errors.append(str(e))
        except Exception as e:
            errors.append(str(e))

    return {
        "minted": minted,
        "failed": len(errors),
        "tx_hashes": tx_hashes,
        "nftoken_ids": nft_ids,
        "nft_price_usd": nft_price_usd,
    }


def _sync_xrpl_single_offer(
    db: Session,
    *,
    artwork_id: int,
    artist_address: str,
) -> Dict[str, Any]:
    """단일 NFT 오퍼 생성 함수"""
    logging.info(f"Starting single offer creation for artwork_id={artwork_id}")

    client = _xrpl_client()
    seed = settings.platform_seed
    if not seed:
        raise RuntimeError("platform_seed is not configured")
    wallet = Wallet.from_seed(seed)
    classic = wallet.classic_address

    # 단일 NFT 로드
    nft: Optional[NFT] = (
        db.query(NFT)
        .filter(NFT.artwork_id == artwork_id)
        .filter(NFT.owner_address == classic)
        .filter(NFT.nftoken_id.isnot(None))
        .filter(NFT.status.in_(["minted", "offered_to_artist"]))
        .first()
    )

    if not nft:
        logging.error("No NFT found for single offer creation")
        return {
            "offers_created": 0,
            "offers_total_considered": 0,
            "offer_ids": [],
            "offer_tx_hashes": [],
            "failed": 1,
            "errors": ["No NFT found"],
        }

    # 이미 offer_id 있으면 스킵
    existing_offer_id = (nft.extra or {}).get("gift_offer_id")
    if existing_offer_id:
        logging.info(f"NFT {nft.id} already has offer_id={existing_offer_id}")
        return {
            "offers_created": 0,
            "offers_total_considered": 1,
            "offer_ids": [existing_offer_id],
            "offer_tx_hashes": [(nft.extra or {}).get("gift_offer_tx_hash")],
            "failed": 0,
            "errors": [],
        }

    try:
        logging.info(f"Creating single offer for NFT {nft.id}")
        # Convert USD price to XRP drops (1 XRP = 1,000,000 drops)
        # For simplicity, using 1 USD = 2 XRP rate (adjustable)
        usd_to_xrp_rate = 2.0  # 1 USD = 2 XRP
        price_xrp = nft.price * usd_to_xrp_rate
        price_drops = str(int(price_xrp * 1_000_000))  # Convert to drops

        res = _create_nft_offer(
            client=client,
            wallet=wallet,
            nftoken_id=nft.nftoken_id,
            destination=artist_address,
            price_drops=price_drops,
        )

        oid = _extract_offer_index(res)
        logging.info(f"Single offer created: offer_id={oid}, tx_hash={res.get('hash')}")

        # DB 업데이트
        extra = nft.extra or {}
        extra.update({
            "gift_offer_id": oid,
            "gift_offer_tx_hash": res.get("hash"),
            "gift_offer_destination": artist_address,
            "gift_offer_amount": price_drops,
            "gift_offer_price_usd": nft.price,
        })
        nft.status = "offered_to_artist"
        nft.extra = extra
        db.add(nft)
        db.commit()

        return {
            "offers_created": 1,
            "offers_total_considered": 1,
            "offer_ids": [oid],
            "offer_tx_hashes": [res.get("hash")],
            "failed": 0,
            "errors": [],
        }

    except Exception as e:
        logging.error(f"Error creating single offer: {str(e)}")
        return {
            "offers_created": 0,
            "offers_total_considered": 1,
            "offer_ids": [None],
            "offer_tx_hashes": [None],
            "failed": 1,
            "errors": [str(e)],
        }


def _sync_xrpl_multi_offer(
    db: Session,
    *,
    artwork_id: int,
    artist_address: str,
) -> Dict[str, Any]:
    """다중 NFT 배치 오퍼 생성 함수"""
    logging.info(f"Starting batch offer creation for artwork_id={artwork_id}")

    client = _xrpl_client()
    seed = settings.platform_seed
    if not seed:
        raise RuntimeError("platform_seed is not configured")
    wallet = Wallet.from_seed(seed)
    classic = wallet.classic_address

    # 이 작품의 '플랫폼이 보유 중'인 NFT 목록 로드 (오퍼가 없는 것만)
    rows: List[NFT] = (
        db.query(NFT)
        .filter(NFT.artwork_id == artwork_id)
        .filter(NFT.owner_address == classic)
        .filter(NFT.nftoken_id.isnot(None))
        .filter(NFT.status == "minted")  # 아직 오퍼가 없는 것만
        .all()
    )

    logging.info(f"Found {len(rows)} NFTs to process for batch offers")

    if not rows:
        return {
            "offers_created": 0,
            "offers_total_considered": 0,
            "offer_ids": [],
            "offer_tx_hashes": [],
            "failed": 0,
            "errors": [],
        }

    # Prepare all NFTokenCreateOffer transactions for batch
    raw_transactions = []
    nft_data = []

    for r in rows:
        # Convert USD price to XRP drops
        usd_to_xrp_rate = 2.0  # 1 USD = 2 XRP
        price_xrp = r.price * usd_to_xrp_rate
        price_drops = str(int(price_xrp * 1_000_000))  # Convert to drops

        offer_tx = NFTokenCreateOffer(
            account=classic,
            nftoken_id=r.nftoken_id,
            amount=price_drops,       # 실제 가격 (drops)
            destination=artist_address,  # 작가 지갑 주소
            flags=1,                  # tfSellNFToken
        )

        raw_transactions.append(offer_tx)
        nft_data.append({
            "nft_id": r.id,
            "nftoken_id": r.nftoken_id,
            "nft_record": r,
            "price_drops": price_drops,
            "price_usd": r.price,
        })

    # Process transactions in chunks of 4 (XRPL batch limit)
    BATCH_SIZE = 4

    logging.info(f"Total offer transactions to process: {len(raw_transactions)}")
    logging.info(f"Processing in chunks of {BATCH_SIZE}")

    # Initialize result containers
    all_offer_ids = []
    all_tx_hashes = []
    total_created = 0
    all_errors = []

    # Process transactions in chunks
    for chunk_idx in range(0, len(raw_transactions), BATCH_SIZE):
        chunk_transactions = raw_transactions[chunk_idx:chunk_idx + BATCH_SIZE]
        chunk_nft_data = nft_data[chunk_idx:chunk_idx + BATCH_SIZE]
        chunk_num = (chunk_idx // BATCH_SIZE) + 1

        logging.info(f"Processing offer chunk {chunk_num} with {len(chunk_transactions)} transactions")

        if len(chunk_transactions) == 1:
            # Process single transaction individually
            try:
                logging.info(f"Processing single offer in chunk {chunk_num}...")

                single_tx = chunk_transactions[0]
                single_nft_data = chunk_nft_data[0]

                # Submit individual transaction
                tx_autofilled = autofill(single_tx, client)
                tx_signed = sign(tx_autofilled, wallet)
                tx_resp = submit_and_wait(tx_signed, client)

                if tx_resp.is_successful():
                    tx_hash = tx_resp.result.get("hash")
                    offer_id = _extract_offer_index(tx_resp.result)

                    all_tx_hashes.append(tx_hash)
                    all_offer_ids.append(offer_id)
                    total_created += 1

                    # Update NFT record
                    nft_record = single_nft_data["nft_record"]
                    extra = nft_record.extra or {}
                    extra.update({
                        "gift_offer_id": offer_id,
                        "gift_offer_tx_hash": tx_hash,
                        "gift_offer_destination": artist_address,
                        "gift_offer_amount": single_nft_data["price_drops"],
                        "gift_offer_price_usd": single_nft_data["price_usd"],
                    })
                    nft_record.status = "offered_to_artist"
                    nft_record.extra = extra
                    db.add(nft_record)
                    db.commit()

                    logging.info(f"Single offer successful: offer_id={offer_id}")
                else:
                    logging.error(f"Single offer failed: {tx_resp.result}")
                    all_errors.append(f"Single offer failed: {tx_resp.result}")
                    all_tx_hashes.append(None)
                    all_offer_ids.append(None)

            except Exception as e:
                logging.error(f"Error in single offer: {str(e)}")
                all_errors.append(f"Single offer error: {str(e)}")
                all_tx_hashes.append(None)
                all_offer_ids.append(None)
        else:
            # Process as batch transaction (2 or more transactions)
            from xrpl.models.transactions import Batch

            try:
                logging.info(f"Submitting offer batch chunk {chunk_num}...")

                # Create batch transaction for this chunk
                batch_tx = Batch(
                    account=classic,
                    raw_transactions=chunk_transactions,
                    flags=65536,  # tfSpike flag for batch transaction
                )

                # Submit batch transaction
                batch_autofilled = autofill(batch_tx, client)
                batch_signed = sign(batch_autofilled, wallet)
                batch_resp = submit_and_wait(batch_signed, client)

                logging.info(f"Offer batch chunk {chunk_num} response: success={batch_resp.is_successful()}")

                if batch_resp.is_successful():
                    batch_hash = batch_resp.result.get("hash")
                    logging.info(f"Offer batch chunk {chunk_num} successful with hash: {batch_hash}")

                    # For batch offers, we can't extract individual offer IDs reliably
                    # So we'll store None for offer_id and use batch_hash
                    for i, nft_info in enumerate(chunk_nft_data):
                        all_tx_hashes.append(batch_hash)
                        all_offer_ids.append(None)  # Batch doesn't expose individual offer IDs
                        total_created += 1

                        # Update NFT record
                        nft_record = nft_info["nft_record"]
                        extra = nft_record.extra or {}
                        extra.update({
                            "gift_offer_id": None,  # Not available in batch response
                            "gift_offer_tx_hash": batch_hash,
                            "gift_offer_destination": artist_address,
                            "gift_offer_amount": nft_info["price_drops"],
                            "gift_offer_price_usd": nft_info["price_usd"],
                            "batch_offer": True,
                            "batch_chunk": chunk_num,
                        })
                        nft_record.status = "offered_to_artist"
                        nft_record.extra = extra
                        db.add(nft_record)

                    db.commit()
                    logging.info(f"Successfully processed offer batch chunk {chunk_num}")
                else:
                    logging.error(f"Offer batch chunk {chunk_num} failed: {batch_resp.result}")
                    all_errors.append(f"Batch chunk {chunk_num} failed: {batch_resp.result}")

                    # Add None entries for failed batch
                    for _ in chunk_nft_data:
                        all_tx_hashes.append(None)
                        all_offer_ids.append(None)

            except Exception as e:
                logging.error(f"Error in offer batch chunk {chunk_num}: {str(e)}")
                all_errors.append(f"Batch chunk {chunk_num} error: {str(e)}")

                # Add None entries for failed batch
                for _ in chunk_nft_data:
                    all_tx_hashes.append(None)
                    all_offer_ids.append(None)

    logging.info(f"Batch offer processing complete. Total created: {total_created}, Total errors: {len(all_errors)}")

    return {
        "offers_created": total_created,
        "offers_total_considered": len(rows),
        "offer_ids": all_offer_ids,
        "offer_tx_hashes": all_tx_hashes,
        "failed": len(all_errors),
        "errors": all_errors,
    }


def _sync_xrpl_batch_offer(
    db: Session,
    *,
    artwork_id: int,
    artist_address: str,
) -> Dict[str, Any]:
    """XRPL 오퍼 생성 라우팅 함수 - 단일/다중 처리 분기"""
    print(f"🚀 OFFER ROUTING START: artwork_id={artwork_id}, artist_address={artist_address}")
    logging.info(f"Starting offer creation routing for artwork_id={artwork_id}")

    # NFT 개수 확인
    seed = settings.platform_seed
    if not seed:
        raise RuntimeError("platform_seed is not configured")
    wallet = Wallet.from_seed(seed)
    classic = wallet.classic_address

    print(f"💰 PLATFORM WALLET: {classic}")

    nft_count = (
        db.query(NFT)
        .filter(NFT.artwork_id == artwork_id)
        .filter(NFT.owner_address == classic)
        .filter(NFT.nftoken_id.isnot(None))
        .filter(NFT.status.in_(["minted", "offered_to_artist"]))
        .count()
    )

    print(f"📊 NFT COUNT: {nft_count}")
    logging.info(f"Found {nft_count} NFTs for offer creation")

    # Debug: Show all NFTs found
    nfts_debug = (
        db.query(NFT)
        .filter(NFT.artwork_id == artwork_id)
        .filter(NFT.owner_address == classic)
        .filter(NFT.nftoken_id.isnot(None))
        .filter(NFT.status.in_(["minted", "offered_to_artist"]))
        .all()
    )

    print(f"🔍 NFTS FOUND: {len(nfts_debug)}")
    for i, nft in enumerate(nfts_debug):
        print(f"  NFT {i+1}: id={nft.id}, nftoken_id={nft.nftoken_id}, status={nft.status}")
        logging.info(f"NFT {i+1}: id={nft.id}, nftoken_id={nft.nftoken_id}, status={nft.status}")

    if nft_count == 0:
        print("❌ NO NFTS FOUND FOR OFFER CREATION!")
        logging.warning("No NFTs found for offer creation!")
        return {
            "offers_created": 0,
            "offers_total_considered": 0,
            "offer_ids": [],
            "offer_tx_hashes": [],
            "failed": 0,
            "errors": [],
        }
    elif nft_count == 1:
        print("➡️ ROUTING TO SINGLE NFT OFFER")
        logging.info("Routing to single NFT offer")
        result = _sync_xrpl_single_offer(
            db=db,
            artwork_id=artwork_id,
            artist_address=artist_address,
        )
        print(f"✅ SINGLE OFFER RESULT: {result}")
        return result
    else:
        print(f"➡️ ROUTING TO MULTI NFT OFFER ({nft_count} NFTs)")
        logging.info(f"Routing to multi NFT offer for {nft_count} NFTs")
        result = _sync_xrpl_multi_offer(
            db=db,
            artwork_id=artwork_id,
            artist_address=artist_address,
        )
        print(f"✅ MULTI OFFER RESULT: {result}")
        return result


async def register_to_ipfs_and_mint(
    db: Session,
    *,
    # 업로드/메타데이터 입력
    image_bytes: bytes,
    image_filename: str,
    title: str,
    description: str,
    year: str,
    size_label: str,
    medium: str,
    price_usd: int,
    grid_n: int,
    artist_address: str,
    # XRPL 민팅 옵션
    flags: int,
    transfer_fee: int,
    taxon: int,
) -> Dict[str, Any]:
    """
    1) 이미지 Pinata 업로드
    2) meta.json 생성 후 Pinata 업로드
    3) Artwork 저장
    4) XRPL TicketCreate + 배치 민팅 (스레드에서 실행)
    5) 각 NFT를 DB에 저장
    6) 모든 민팅이 끝나면 한꺼번에 오퍼 생성 (스레드)
    """
    # 1) 이미지 업로드
    img_res = await pin_file_to_ipfs(
        file_bytes=image_bytes,
        filename=image_filename or "artwork.png",
        metadata={"name": f"art_{title}"},
    )
    image_cid = img_res["IpfsHash"]
    image_uri = f"ipfs://{image_cid}/{image_filename}"

    # 2) meta.json 구성 & 업로드
    attributes = []
    if year:
        attributes.append({"trait_type": "제작연도", "value": year})
    if size_label:
        attributes.append({"trait_type": "크기", "value": size_label})
    if medium:
        attributes.append({"trait_type": "재료", "value": medium})

    metadata = {
        "name": title,
        "description": description or "",
        "image": image_uri,
        "attributes": attributes,
    }
    meta_res = await pin_json_to_ipfs(metadata, name=f"meta_{title}")
    metadata_cid = meta_res["IpfsHash"]
    metadata_uri_base = f"ipfs://{metadata_cid}/meta.json"
    metadata_http_url = f"{settings.pinata_gateway}/{metadata_cid}/meta.json"

    # 3) Artwork 저장
    grid_total = grid_n * grid_n
    artwork = Artwork(
        title=title,
        description=description,
        size=size_label,
        price_usd=price_usd,
        grid_n=grid_n,
        image_url=image_uri,  # 원본 이미지 URI(IPFS)
        metadata_uri_base=metadata_uri_base,
        artist_address=artist_address,
    )
    db.add(artwork)
    db.commit()
    db.refresh(artwork)

    # nft 조각 가격
    nft_price_usd = price_usd // grid_total

    # 4) XRPL 배치 민팅 (스레드에서 실행)
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        mint_result = await loop.run_in_executor(
            executor,
            _sync_xrpl_batch_mint,
            db,
            artwork.id,
            metadata_uri_base,
            grid_total,
            flags,
            transfer_fee,
            taxon,
            nft_price_usd
        )

    # 4) (신규) 모든 민팅이 끝나면 한꺼번에 오퍼 생성 (스레드)
    with ThreadPoolExecutor() as executor:
        offer_result = await loop.run_in_executor(
            executor,
            partial(
                _sync_xrpl_batch_offer,
                db,
                artwork_id=artwork.id,
                artist_address=artist_address,
            ),
        )

    status = (
        "ok"
        if mint_result["minted"] == grid_total
        else ("partial" if mint_result["minted"] > 0 else "failed")
    )

    return {
        "artwork_id": artwork.id,
        "artist_address": artist_address,
        "image_cid": image_cid,
        "image_uri": image_uri,
        "metadata_cid": metadata_cid,
        "metadata_uri_base": metadata_uri_base,
        "metadata_http_url": metadata_http_url,
        "minted": mint_result["minted"],
        "failed": mint_result["failed"],
        "tx_hashes": mint_result["tx_hashes"],
        "nftoken_ids": mint_result["nftoken_ids"],
        "nft_price_usd": mint_result["nft_price_usd"],
        "status": status,
        "offers_created": offer_result["offers_created"],
        "offers_total_considered": offer_result["offers_total_considered"],
        "offer_ids": offer_result["offer_ids"],
        "offer_tx_hashes": offer_result["offer_tx_hashes"],
        "offer_failed": offer_result["failed"],
        "status": status
    }


def verify_tx(tx_hash: str) -> Dict[str, Any]:
    """간단한 트랜잭션 검증 여부 확인 (검증 원하면 확장 가능)."""
    client = _xrpl_client()
    resp = client.request(Tx(transaction=tx_hash))
    r = resp.result
    validated = bool(r.get("validated"))
    return {"validated": validated, "tx_json": r if validated else None}
