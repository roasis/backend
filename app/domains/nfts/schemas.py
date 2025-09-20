from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NFTResponse(BaseModel):
    """NFT response schema"""
    id: int = Field(..., description="NFT ID")
    artwork_id: int = Field(..., description="Associated artwork ID")
    uri_hex: str = Field(..., description="XRPL URI in hex format")
    nftoken_id: Optional[str] = Field(None, description="XRPL NFToken ID")
    tx_hash: Optional[str] = Field(None, description="Minting transaction hash")
    offer_tx_hash: Optional[str] = Field(None, description="Offer transaction hash")
    owner_address: str = Field(..., description="Current owner wallet address")
    status: str = Field(..., description="NFT status (minted/sold)")
    price: int = Field(..., description="Price in USD cents")

    class Config:
        from_attributes = True


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
