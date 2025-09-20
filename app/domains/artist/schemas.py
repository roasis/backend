from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class ArtistCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    profile_image: Optional[str] = Field(default=None, max_length=500)


class ArtistUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    profile_image: Optional[str] = Field(default=None, max_length=500)


class ArtistResponse(BaseModel):
    id: int
    wallet_address: str
    name: str
    email: Optional[str]
    profile_image: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ArtistListResponse(BaseModel):
    id: int
    wallet_address: str
    name: str
    email: Optional[str]
    profile_image: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
