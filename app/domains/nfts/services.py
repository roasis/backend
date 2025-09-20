# import time
# from typing import Any, Dict, List, Optional, Tuple

# from sqlalchemy.orm import Session

# from xrpl.clients import JsonRpcClient
# from xrpl.wallet import Wallet
# from xrpl.models.requests import AccountInfo, AccountObjects, Tx
# from xrpl.models.transactions import TicketCreate, NFTokenMint
# from xrpl.transaction import autofill, sign, submit_and_wait, XRPLReliableSubmissionException
# from xrpl.utils import str_to_hex

# from app.core.config import settings
# from .models import Artwork, NFT
# from app.shared.pinata_client import pin_file_to_ipfs, pin_json_to_ipfs

# DEVNET_URL = "https://s.devnet.rippletest.net:51234/"


# def _xrpl_client() -> JsonRpcClient:
#     rpc = getattr(settings, "xrpl_rpc_url", DEVNET_URL) or DEVNET_URL
#     return JsonRpcClient(rpc)


# def _assert_funded(client: JsonRpcClient, address: str) -> int:
#     req = AccountInfo(account=address, ledger_index="validated", strict=True)
#     resp = client.request(req)
#     if "account_data" not in resp.result:
#         raise RuntimeError(f"account_info failed: {resp.result}")
#     return int(resp.result["account_data"]["Sequence"])


# def _get_ticket_sequences(client: JsonRpcClient, address: str, want: int) -> List[int]:
#     req = AccountObjects(account=address, type="ticket")
#     resp = client.request(req)
#     objs = resp.result.get("account_objects", [])
#     tickets = [int(o["TicketSequence"]) for o in objs]
#     tickets.sort()
#     return tickets[:want]


# def _extract_minted_id(tx_result: Dict[str, Any]) -> Optional[str]:
#     nft_id = tx_result.get("meta", {}).get("nftoken_id")
#     if nft_id:
#         return nft_id
#     meta = tx_result.get("meta") or {}
#     nodes = meta.get("AffectedNodes") or []
#     for n in nodes:
#         created = (n.get("CreatedNode") or {})
#         if created.get("LedgerEntryType") == "NFToken":
#             fields = created.get("NewFields") or {}
#             if "NFTokenID" in fields:
#                 return fields["NFTokenID"]
#     return None


# def _build_part_uri(base: str, idx: int, total: int) -> str:
#     # 조각별 고유 URI (원하면 포맷 수정)
#     return f"{base}?p={idx}&t={total}"

# async def register_to_ipfs_and_mint(
#     db: Session,
#     *,
#     # 업로드/메타데이터 입력
#     image_bytes: bytes,
#     image_filename: str,
#     title: str,
#     description: str,
#     year: str,
#     size_label: str,
#     medium: str,
#     price_usd: int,
#     grid_n: int,
#     artist_address: str,

#     # XRPL 민팅 옵션
#     flags: int,
#     transfer_fee: int,
#     taxon: int,
# ) -> Dict[str, Any]:
#     """
#     1) 이미지 Pinata 업로드
#     2) meta.json 생성 후 Pinata 업로드
#     3) Artwork 저장
#     4) XRPL TicketCreate + 배치 민팅
#     5) 각 NFT를 DB에 저장
#     """
#     # 1) 이미지 업로드
#     img_res = await pin_file_to_ipfs(
#         file_bytes=image_bytes,
#         filename=image_filename or "artwork.png",
#         metadata={"name": f"art_{title}"}
#     )
#     image_cid = img_res["IpfsHash"]
#     image_uri = f"ipfs://{image_cid}/{image_filename}"

#     # 2) meta.json 구성 & 업로드
#     attributes = []
#     if year: attributes.append({"trait_type": "제작연도", "value": year})
#     if size_label: attributes.append({"trait_type": "크기", "value": size_label})
#     if medium: attributes.append({"trait_type": "재료", "value": medium})

#     metadata = {
#         "name": title,
#         "description": description or "",
#         "image": image_uri,
#         "attributes": attributes,
#     }
#     meta_res = await pin_json_to_ipfs(metadata, name=f"meta_{title}")
#     metadata_cid = meta_res["IpfsHash"]
#     metadata_uri_base = f"ipfs://{metadata_cid}/meta.json"
#     metadata_http_url = f"{settings.pinata_gateway}/{metadata_cid}/meta.json"

#     # 3) Artwork 저장
#     grid_total = grid_n * grid_n
#     artwork = Artwork(
#         title=title,
#         description=description,
#         size=size_label,
#         price_usd=price_usd,
#         grid_n=grid_n,
#         image_url=image_uri,               # 원본 이미지 URI(IPFS)
#         metadata_uri_base=metadata_uri_base,
#         artist_address=artist_address,
#     )
#     db.add(artwork)
#     db.commit()
#     db.refresh(artwork)

#     # 4) XRPL 배치 민팅
#     client = _xrpl_client()
#     seed = settings.platform_seed
#     if not seed:
#         raise RuntimeError("platform_seed is not configured")
#     wallet = Wallet.from_seed(seed)
#     classic = wallet.classic_address

#     current_seq = _assert_funded(client, classic)
#     tc = TicketCreate(account=classic, ticket_count=grid_total, sequence=current_seq)
#     tc_autofilled = autofill(tc, client)
#     tc_signed = sign(tc_autofilled, wallet)
#     tc_resp = submit_and_wait(tc_signed, client)
#     if not tc_resp.is_successful():
#         raise RuntimeError(f"TicketCreate failed: {tc_resp.result}")

#     # 티켓 조회(지연 보정)
#     time.sleep(0.5)
#     tickets = _get_ticket_sequences(client, classic, grid_total)
#     if len(tickets) < grid_total:
#         time.sleep(1.0)
#         tickets = _get_ticket_sequences(client, classic, grid_total)
#     if len(tickets) < grid_total:
#         raise RuntimeError(f"Not enough tickets: want={grid_total}, got={len(tickets)}")

#     minted = 0
#     tx_hashes: List[str] = []
#     nft_ids: List[Optional[str]] = []
#     errors: List[Any] = []

#     for i, tseq in enumerate(tickets[:grid_total], start=1):
#         part_uri = _build_part_uri(metadata_uri_base, i, grid_total)
#         uri_hex = str_to_hex(part_uri)

#         mint_tx = NFTokenMint(
#             account=classic,
#             uri=uri_hex,
#             flags=int(flags),
#             transfer_fee=int(transfer_fee),
#             ticket_sequence=int(tseq),
#             sequence=0,
#             nftoken_taxon=int(taxon),
#         )
#         try:
#             m_autofilled = autofill(mint_tx, client)
#             m_signed = sign(m_autofilled, wallet)
#             m_resp = submit_and_wait(m_signed, client)

#             if m_resp.is_successful():
#                 minted += 1
#                 txh = m_resp.result.get("hash")
#                 nid = _extract_minted_id(m_resp.result)
#                 tx_hashes.append(txh)
#                 nft_ids.append(nid)

#                 db.add(
#                     NFT(
#                         artwork_id=artwork.id,
#                         uri_hex=uri_hex,
#                         nftoken_id=nid,
#                         tx_hash=txh,
#                         owner_address=classic,
#                         status="minted",
#                         extra={"part_uri": part_uri, "grid_index": i, "grid_total": grid_total},
#                     )
#                 )
#                 db.commit()
#             else:
#                 errors.append(m_resp.result)

#         except XRPLReliableSubmissionException as e:
#             errors.append(str(e))
#         except Exception as e:
#             errors.append(str(e))

#     status = "ok" if minted == grid_total else ("partial" if minted > 0 else "failed")
#     return {
#         "artwork_id": artwork.id,
#         "image_cid": image_cid,
#         "image_uri": image_uri,
#         "metadata_cid": metadata_cid,
#         "metadata_uri_base": metadata_uri_base,
#         "metadata_http_url": metadata_http_url,
#         "minted": minted,
#         "failed": len(errors),
#         "tx_hashes": tx_hashes,
#         "nftoken_ids": nft_ids,
#         "status": status,
#     }


# def verify_tx(tx_hash: str) -> Dict[str, Any]:
#     """간단한 트랜잭션 검증 여부 확인 (검증 원하면 확장 가능)."""
#     client = _xrpl_client()
#     resp = client.request(Tx(transaction=tx_hash))
#     r = resp.result
#     validated = bool(r.get("validated"))
#     return {"validated": validated, "tx_json": r if validated else None}

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from xrpl.clients import JsonRpcClient
from xrpl.models.requests import AccountInfo, AccountObjects, Tx
from xrpl.models.transactions import NFTokenMint, TicketCreate
from xrpl.transaction import XRPLReliableSubmissionException, autofill, sign, submit_and_wait
from xrpl.utils import str_to_hex
from xrpl.wallet import Wallet

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


def _sync_xrpl_batch_mint(
    db: Session,
    artwork_id: int,
    metadata_uri_base: str,
    grid_total: int,
    flags: int,
    transfer_fee: int,
    taxon: int,
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
        )

    status = (
        "ok"
        if mint_result["minted"] == grid_total
        else ("partial" if mint_result["minted"] > 0 else "failed")
    )

    return {
        "artwork_id": artwork.id,
        "image_cid": image_cid,
        "image_uri": image_uri,
        "metadata_cid": metadata_cid,
        "metadata_uri_base": metadata_uri_base,
        "metadata_http_url": metadata_http_url,
        "minted": mint_result["minted"],
        "failed": mint_result["failed"],
        "tx_hashes": mint_result["tx_hashes"],
        "nftoken_ids": mint_result["nftoken_ids"],
        "status": status,
    }


def verify_tx(tx_hash: str) -> Dict[str, Any]:
    """간단한 트랜잭션 검증 여부 확인 (검증 원하면 확장 가능)."""
    client = _xrpl_client()
    resp = client.request(Tx(transaction=tx_hash))
    r = resp.result
    validated = bool(r.get("validated"))
    return {"validated": validated, "tx_json": r if validated else None}
