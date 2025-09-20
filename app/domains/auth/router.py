from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.domains.auth import schemas
from app.domains.auth.service import XRPLAuthService
from app.shared.database.connection import get_db

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


@router.post("/login", response_model=schemas.LoginResponse)
def login_with_wallet(
    login_request: schemas.WalletLoginRequest, db: Session = Depends(get_db)
):
    """
    Login with XRPL wallet signature

    The message should be a consistent string like:
    "Login to Roasis with wallet: {wallet_address} at {timestamp}"
    """
    auth_service = XRPLAuthService(db)
    return auth_service.authenticate_wallet(login_request)


@router.get("/me", response_model=schemas.UserInfoResponse)
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Get current authenticated user info
    """
    auth_service = XRPLAuthService(db)
    wallet_auth = auth_service.get_current_wallet(credentials.credentials)
    return schemas.UserInfoResponse(
        wallet_address=wallet_auth.wallet_address,
        last_login=wallet_auth.last_login,
        is_active=wallet_auth.is_active,
    )
