import json
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class GalleryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    description: Optional[str] = None
    website: Optional[str] = Field(default=None, max_length=500)
    profile_image: Optional[str] = Field(default=None, max_length=500)
    file_urls: Optional[List[str]] = Field(
        default=None, description="List of file URLs"
    )


class GalleryResponse(BaseModel):
    id: int
    wallet_address: str
    name: str
    email: Optional[str]
    description: Optional[str]
    website: Optional[str]
    profile_image: Optional[str]
    file_urls: Optional[List[str]]
    created_at: datetime
    updated_at: datetime

    @field_validator("file_urls", mode="before")
    @classmethod
    def parse_file_urls(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return v

    class Config:
        from_attributes = True
