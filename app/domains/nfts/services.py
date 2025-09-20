import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from xrpl.clients import JsonRpcClient
from xrpl.models.requests import AccountInfo, AccountObjects, Tx
from xrpl.models.transactions import NFTokenMint, TicketCreate, NFTokenCreateOffer, Batch
from xrpl.transaction import XRPLReliableSubmissionException, autofill, sign, submit_and_wait
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


def _create_zero_amount_gift_offer(
    client: JsonRpcClient,
    wallet: Wallet,
    nftoken_id: str,
    destination: str,
) -> Dict[str, Any]:
    offer_tx = NFTokenCreateOffer(
        account=wallet.classic_address,
        nftoken_id=nftoken_id,
        amount="0",               # 0 drop = 선물
        destination=destination,  # 작가 지갑 주소
        flags=1,                  # tfSellNFToken
    )
    o_autofilled = autofill(offer_tx, client)
    o_signed = sign(o_autofilled, wallet)
    o_resp = submit_and_wait(o_signed, client)
    return o_resp.result


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

    # Prepare all NFTokenMint transactions for batch
    raw_transactions = []
    nft_data = []

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

        raw_transactions.append(mint_tx)
        nft_data.append({
            "part_uri": part_uri,
            "uri_hex": uri_hex,
            "grid_index": i,
            "grid_total": grid_total,
        })

    # Create batch transaction with flags 0x00010000
    batch_tx = Batch(
        account=classic,
        raw_transactions=raw_transactions,
        flags=0x00010000,  # tfSpike flag for batch transaction
    )

    try:
        # Submit batch transaction
        batch_autofilled = autofill(batch_tx, client)
        batch_signed = sign(batch_autofilled, wallet)
        batch_resp = submit_and_wait(batch_signed, client)

        tx_hashes = []
        nft_ids = []
        minted = 0
        errors = []

        if batch_resp.is_successful():
            batch_hash = batch_resp.result.get("hash")

            # Process each NFT in the batch
            for i, nft_info in enumerate(nft_data):
                try:
                    # For batch transactions, we need to get individual transaction results
                    # The batch response contains the overall result
                    nft_id = None  # Will be extracted from transaction metadata or subsequent queries

                    tx_hashes.append(batch_hash)
                    nft_ids.append(nft_id)
                    minted += 1

                    db.add(
                        NFT(
                            artwork_id=artwork_id,
                            uri_hex=nft_info["uri_hex"],
                            nftoken_id=nft_id,
                            tx_hash=batch_hash,
                            owner_address=classic,
                            status="minted",
                            price=nft_price_usd,
                            extra={
                                "part_uri": nft_info["part_uri"],
                                "grid_index": nft_info["grid_index"],
                                "grid_total": nft_info["grid_total"],
                                "batch_transaction": True,
                            },
                        )
                    )
                except Exception as e:
                    errors.append(f"Error processing NFT {i+1}: {str(e)}")

            db.commit()
        else:
            errors.append(batch_resp.result)

    except XRPLReliableSubmissionException as e:
        errors = [str(e)]
        tx_hashes = []
        nft_ids = []
        minted = 0
    except Exception as e:
        errors = [str(e)]
        tx_hashes = []
        nft_ids = []
        minted = 0

    return {
        "minted": minted,
        "failed": len(errors),
        "tx_hashes": tx_hashes,
        "nftoken_ids": nft_ids,
        "nft_price_usd": nft_price_usd,
    }


def _sync_xrpl_batch_offer(
    db: Session,
    *,
    artwork_id: int,
    artist_address: str,
) -> Dict[str, Any]:
    client = _xrpl_client()
    seed = settings.platform_seed
    if not seed:
        raise RuntimeError("platform_seed is not configured")
    wallet = Wallet.from_seed(seed)
    classic = wallet.classic_address

    # 이 작품의 '플랫폼이 보유 중'인 NFT 목록 로드
    rows: List[NFT] = (
        db.query(NFT)
        .filter(NFT.artwork_id == artwork_id)
        .filter(NFT.owner_address == classic)
        .filter(NFT.nftoken_id.isnot(None))
        .filter(NFT.status.in_(["minted", "offered_to_artist"]))  # 재시도 안전
        .all()
    )

    created = 0
    offer_ids: List[Optional[str]] = []
    offer_tx_hashes: List[Optional[str]] = []
    errors: List[Any] = []

    for r in rows:
        # 이미 offer_id 있으면 스킵(재진입 대비)
        existing_offer_id = (r.extra or {}).get("gift_offer_id")
        if existing_offer_id:
            offer_ids.append(existing_offer_id)
            offer_tx_hashes.append((r.extra or {}).get("gift_offer_tx_hash"))
            continue

        try:
            res = _create_zero_amount_gift_offer(
                client=client,
                wallet=wallet,
                nftoken_id=r.nftoken_id,
                destination=artist_address,
            )
            oid = _extract_offer_index(res)
            offer_ids.append(oid)
            offer_tx_hashes.append(res.get("hash"))
            created += 1

            # DB 업데이트
            extra = r.extra or {}
            extra.update({
                "gift_offer_id": oid,
                "gift_offer_tx_hash": res.get("hash"),
                "gift_offer_destination": artist_address,
                "gift_offer_amount": "0",
            })
            r.status = "offered_to_artist"
            r.extra = extra
            db.add(r)
            db.commit()

        except Exception as e:
            errors.append(str(e))
            offer_ids.append(None)
            offer_tx_hashes.append(None)

    return {
        "offers_created": created,
        "offers_total_considered": len(rows),
        "offer_ids": offer_ids,
        "offer_tx_hashes": offer_tx_hashes,
        "failed": len(errors),
        "errors": errors,
    }


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
