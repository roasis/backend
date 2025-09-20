from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field

from app.domains.auth.models import UserType


class WalletLoginRequest(BaseModel):
    wallet_address: str


class JwtResponse(BaseModel):
    access_token: str


class TokenData(BaseModel):
    wallet_address: Optional[str] = None
    user_type: Optional[UserType] = None


class BasicProfileRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    profile_image: Optional[str] = Field(default=None, max_length=500)


class GalleryProfileRequest(BasicProfileRequest):
    description: Optional[str] = None
    website: Optional[str] = Field(default=None, max_length=500)
    file_urls: Optional[List[str]] = Field(
        default=None, description="List of file URLs"
    )


class BasicWalletRegisterRequest(BaseModel):
    wallet_address: str
    profile: BasicProfileRequest


class GalleryWalletRegisterRequest(BaseModel):
    wallet_address: str
    profile: GalleryProfileRequest


class UserInfoResponse(BaseModel):
    user_type: UserType
    last_login: datetime
    is_active: bool
