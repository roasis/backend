from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class GalleryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=30)
    location: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None


class GalleryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=30)
    location: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None


class GalleryResponse(BaseModel):
    id: int
    name: str
    phone: Optional[str]
    location: Optional[str]
    description: Optional[str]
    owner_wallet_address: str
    created_at: datetime

    class Config:
        from_attributes = True
