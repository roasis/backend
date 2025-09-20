from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.domains.auth.models import UserType


class WalletLoginRequest(BaseModel):
    wallet_address: str
    signature: str
    message: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    wallet_address: Optional[str] = None


class WalletRegisterRequest(BaseModel):
    wallet_address: str
    signature: str
    message: str
    user_type: UserType


class WalletRegisterResponse(BaseModel):
    user_type: UserType
    created_at: datetime
    message: str = "Wallet registered successfully"


class UserInfoResponse(BaseModel):
    user_type: UserType
    last_login: datetime
    is_active: bool
