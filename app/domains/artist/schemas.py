from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class ArtistUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    profile_image_url: Optional[str] = Field(default=None, max_length=500)


class ArtistResponse(BaseModel):
    id: int
    wallet_address: str
    name: str
    email: Optional[str]
    profile_image_url: Optional[str]
    gallery_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ArtistListResponse(BaseModel):
    id: int
    wallet_address: str
    name: str
    email: Optional[str]
    profile_image_url: Optional[str]
    gallery_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class ArtistInviteRequest(BaseModel):
    artist_wallet_address: str = Field(..., description="Artist's wallet address to invite")


class ArtistInviteResponse(BaseModel):
    message: str
    artist_id: int
    gallery_id: int
