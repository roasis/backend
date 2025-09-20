from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from xrpl.clients import JsonRpcClient
from xrpl.models.requests import Tx, LedgerEntry

from app.core.config import settings
from app.shared.database.connection import get_db
from app.domains.nfts.models import NFT

router = APIRouter(prefix="/nfts", tags=["NFT Purchase"])


# ----------------------------
# Utils
# ----------------------------
def build_accept_sell_offer_tx_json(buyer_address: str, sell_offer_id: str) -> dict:
    """구매자가 특정 Sell Offer를 수락하기 위한 트랜잭션 JSON 생성"""
    return {
        "TransactionType": "NFTokenAcceptOffer",
        "Account": buyer_address,
        "NFTokenSellOffer": sell_offer_id,
    }


def _get_offer_owner(client: JsonRpcClient, offer_id: str) -> str | None:
    """LedgerEntry로부터 오퍼의 Owner 주소 확인"""
    resp = client.request(LedgerEntry(index=offer_id, ledger_index="validated"))
    node = (resp.result or {}).get("node") or {}
    if node.get("LedgerEntryType") == "NFTokenOffer":
        return node.get("Owner")
    return None


# ----------------------------
# API Endpoints
# ----------------------------
@router.get("/{nft_id}/sell-accept/txjson")
def get_sell_accept_txjson(
    nft_id: int,
    buyer_address: str = Query(..., description="구매자 XRPL 주소"),
    db: Session = Depends(get_db),
):
    """
    구매자가 직접 서명할 수 있도록 NFTokenAcceptOffer 트랜잭션 JSON 생성.
    """
    nft = db.query(NFT).filter(NFT.id == nft_id).first()
    if not nft or not nft.nftoken_id:
        raise HTTPException(404, "NFT not found or not minted")

    sell_offer_id = (nft.extra or {}).get("sell_offer_id")
    if not sell_offer_id:
        raise HTTPException(400, "Sell offer not recorded")

    tx_json = build_accept_sell_offer_tx_json(buyer_address, sell_offer_id)
    return {
        "tx_json": tx_json,
        "sell_offer_id": sell_offer_id,
        "nftoken_id": nft.nftoken_id,
    }


@router.post("/{nft_id}/sell-accept/confirm")
def confirm_sell_accept(
    nft_id: int,
    tx_hash: str,
    buyer_address: str,
    db: Session = Depends(get_db),
):
    """
    구매자가 Sell Offer를 Accept한 뒤 tx_hash를 받아 DB에 반영.
    """
    nft = db.query(NFT).filter(NFT.id == nft_id).first()
    if not nft:
        raise HTTPException(404, "NFT not found")

    sell_offer_id = (nft.extra or {}).get("sell_offer_id")
    if not sell_offer_id:
        raise HTTPException(400, "Sell offer not recorded")

    client = JsonRpcClient(settings.xrpl_rpc_url)

    # 트랜잭션 검증
    txr = client.request(Tx(transaction=tx_hash)).result
    if not txr.get("validated"):
        raise HTTPException(400, "Transaction not validated yet")

    # (선택) 오퍼 소유자 확인
    offer_owner = _get_offer_owner(client, sell_offer_id)
    if not offer_owner:
        # 오퍼가 체결되어 이미 소멸했을 수 있음 → 스킵
        pass

    # DB 업데이트
    extra = (nft.extra or {}).copy()
    extra.update(
        {
            "sell_accept_tx_hash": tx_hash,
            "sold_via": "direct_accept",
        }
    )
    nft.owner_address = buyer_address
    nft.status = "sold"
    nft.extra = extra
    db.add(nft)
    db.commit()

    return {
        "ok": True,
        "nft_id": nft_id,
        "new_owner": buyer_address,
        "tx_hash": tx_hash,
    }
