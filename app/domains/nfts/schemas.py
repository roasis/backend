from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# 업로드+민팅 한번에 처리할 입력
class RegisterMintOut(BaseModel):
    artwork_id: int
    image_cid: str
    image_uri: str
    metadata_cid: str
    metadata_uri_base: str  # ipfs://<cid>/meta.json
    metadata_http_url: str  # 게이트웨이 URL
    minted: int
    failed: int
    tx_hashes: List[str]
    nftoken_ids: List[Optional[str]]
    status: str


# 별도 검증용(선택)
class VerifyIn(BaseModel):
    tx_hash: str


class VerifyOut(BaseModel):
    validated: bool
    tx_json: Dict[str, Any] | None = None


class BrokerRequest(BaseModel):
    sell_offer_id: str
    buy_offer_id: str
