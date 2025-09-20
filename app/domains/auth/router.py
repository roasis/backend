from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.domains.auth import schemas
from app.domains.auth.service import XRPLAuthService
from app.shared.database.connection import get_db

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


@router.post("/register", response_model=schemas.JwtResponse)
def register_wallet(
    register_request: schemas.WalletRegisterRequest, db: Session = Depends(get_db)
):
    """
    Register a new XRPL wallet

    The message should be a consistent string like:
    "Register to Roasis with wallet: {wallet_address} at {timestamp}"

    **Possible errors:**
    - 401: Invalid wallet signature
    - 409: Wallet already registered
    - 422: Invalid wallet address format
    """
    auth_service = XRPLAuthService(db)
    return auth_service.register_wallet(register_request)


@router.post("/login", response_model=schemas.JwtResponse)
def login_with_wallet(
    login_request: schemas.WalletLoginRequest, db: Session = Depends(get_db)
):
    """
    Login with XRPL wallet signature

    The message should be a consistent string like:
    "Login to Roasis with wallet: {wallet_address} at {timestamp}"

    **Possible errors:**
    - 401: Invalid wallet signature
    - 403: Wallet not registered (register first using /auth/register)
    - 422: Missing required fields (wallet_address, signature, message)
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

    **Possible errors:**
    - 401: Invalid or expired token, missing Authorization header
    - 404: Wallet not found (token valid but wallet was deleted)
    """
    auth_service = XRPLAuthService(db)
    wallet_auth = auth_service.get_current_wallet(credentials.credentials)
    return schemas.UserInfoResponse(
        user_type=wallet_auth.user_type,
        last_login=wallet_auth.last_login,
        is_active=wallet_auth.is_active,
    )
