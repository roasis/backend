from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class WalletLoginRequest(BaseModel):
    wallet_address: str
    signature: str
    message: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    wallet_address: Optional[str] = None


class UserInfoResponse(BaseModel):
    wallet_address: str
    last_login: datetime
    is_active: bool
