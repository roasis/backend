from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.domains.nfts.schemas import NFTResponse


class ArtworkResponse(BaseModel):
    """Artwork response schema"""
    id: int
    title: str = Field(..., description="Artwork title")
    description: str = Field(..., description="Artwork description")
    size: str = Field(..., description="Artwork size (e.g., '2x2', '3x3')")
    price_usd: int = Field(..., description="Price in USD cents")
    grid_n: int = Field(..., description="Grid division size for NFT pieces")
    image_url: str = Field(..., description="Image URL (S3/IPFS)")
    metadata_uri_base: str = Field(..., description="Base URI for metadata (e.g., ipfs://cid/meta.json)")
    artist_address: str = Field(..., description="Artist's XRPL wallet address")
    created_at: datetime = Field(..., description="Creation timestamp")
    nfts: Optional[List[NFTResponse]] = Field(None, description="List of associated NFTs")

    class Config:
        from_attributes = True


class ArtworkListResponse(BaseModel):
    """Simplified artwork response for list endpoints"""
    id: int
    title: str = Field(..., description="Artwork title")
    size: str = Field(..., description="Artwork size")
    price_usd: int = Field(..., description="Price in USD cents")
    image_url: str = Field(..., description="Image URL")
    artist_address: str = Field(..., description="Artist's XRPL wallet address")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True


class ArtworkUpdateRequest(BaseModel):
    """Artwork update request schema"""
    title: Optional[str] = Field(None, description="Artwork title")
    description: Optional[str] = Field(None, description="Artwork description")
    size: Optional[str] = Field(None, description="Artwork size")
    price_usd: Optional[int] = Field(None, ge=0, description="Price in USD cents")
    grid_n: Optional[int] = Field(None, ge=1, description="Grid division size")
    image_url: Optional[str] = Field(None, description="Image URL")
    metadata_uri_base: Optional[str] = Field(None, description="Base URI for metadata")
