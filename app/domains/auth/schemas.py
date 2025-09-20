from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.domains.auth.models import UserType


class WalletLoginRequest(BaseModel):
    wallet_address: str


class JwtResponse(BaseModel):
    access_token: str


class TokenData(BaseModel):
    wallet_address: Optional[str] = None
    user_type: Optional[UserType] = None


class WalletRegisterRequest(BaseModel):
    wallet_address: str
    user_type: UserType


class UserInfoResponse(BaseModel):
    user_type: UserType
    last_login: datetime
    is_active: bool
