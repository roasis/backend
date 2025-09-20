from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.domains.artist.service import ArtistService
from app.domains.auth import schemas
from app.domains.auth.service import XRPLAuthService
from app.domains.gallery.service import GalleryService
from app.shared.database.connection import get_db

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


@router.post("/register/gallery", response_model=schemas.JwtResponse)
def register_gallery_wallet(
    register_request: schemas.GalleryWalletRegisterRequest,
    db: Session = Depends(get_db),
):
    """
    Register a new XRPL wallet (Gallery)

    **Possible errors:**
    - 409: Wallet already registered
    - 422: Invalid wallet address format
    """
    auth_service = XRPLAuthService(db)
    gallery_service = GalleryService(db)
    gallery_service.create_gallery(
        register_request.profile, register_request.wallet_address
    )
    return auth_service.register_wallet(register_request)


@router.post("/register/artist", response_model=schemas.JwtResponse)
def register_artist_wallet(
    register_request: schemas.BasicWalletRegisterRequest, db: Session = Depends(get_db)
):
    """
    Register a new XRPL wallet (Artist)

    **Possible errors:**
    - 409: Wallet already registered
    - 422: Invalid wallet address format
    """
    auth_service = XRPLAuthService(db)
    artist_service = ArtistService(db)
    artist_service.create_artist(
        register_request.profile, register_request.wallet_address
    )
    return auth_service.register_wallet(register_request)


@router.post("/login", response_model=schemas.JwtResponse)
def login_with_wallet(
    login_request: schemas.WalletLoginRequest, db: Session = Depends(get_db)
):
    """
    Login with XRPL wallet signature

    **Possible errors:**
    - 403: Wallet not registered (register first)
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


# Dependency for protected routes
def get_current_wallet_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Dependency to get current authenticated wallet for protected routes
    """
    auth_service = XRPLAuthService(db)
    return auth_service.get_current_wallet(credentials.credentials)
