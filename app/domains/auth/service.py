from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domains.auth import models, schemas
from app.domains.auth.schemas import GalleryWalletRegisterRequest

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 240


class XRPLAuthService:
    def __init__(self, db: Session):
        self.db = db

    def create_access_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ):
        """
        Create JWT access token
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
        return encoded_jwt

    def verify_token(self, token: str) -> schemas.TokenData:
        """
        Verify JWT token and return token data
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
            wallet_address: str = payload.get("sub")
            if wallet_address is None:
                raise credentials_exception
            user_type_value = payload.get("user_type")
            user_type = models.UserType(user_type_value) if user_type_value else None
            token_data = schemas.TokenData(
                wallet_address=wallet_address, user_type=user_type
            )
        except JWTError:
            raise credentials_exception
        return token_data

    def register_wallet(
        self, register_request: GalleryWalletRegisterRequest
    ) -> schemas.JwtResponse:
        """
        Register a new wallet and return access token
        """

        # Check if wallet already exists
        existing_wallet = (
            self.db.query(models.WalletAuth)
            .filter(models.WalletAuth.wallet_address == register_request.wallet_address)
            .first()
        )

        if existing_wallet:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Wallet already registered",
            )

        # Create new wallet auth record
        wallet_auth = models.WalletAuth(
            wallet_address=register_request.wallet_address,
            user_type=register_request.user_type,
        )
        self.db.add(wallet_auth)
        self.db.commit()
        self.db.refresh(wallet_auth)

        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self.create_access_token(
            data={
                "sub": register_request.wallet_address,
                "user_type": register_request.user_type.value,
            },
            expires_delta=access_token_expires,
        )

        return schemas.JwtResponse(access_token=access_token)

    def authenticate_wallet(
        self, login_request: schemas.WalletLoginRequest
    ) -> schemas.JwtResponse:
        """
        Authenticate wallet and return access token
        """
        # Get or create wallet auth record
        wallet_auth = (
            self.db.query(models.WalletAuth)
            .filter(models.WalletAuth.wallet_address == login_request.wallet_address)
            .first()
        )

        if not wallet_auth:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Wallet not registered. Please register first.",
            )

        wallet_auth.last_login = datetime.utcnow()

        self.db.commit()

        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self.create_access_token(
            data={
                "sub": login_request.wallet_address,
                "user_type": wallet_auth.user_type.value,
            },
            expires_delta=access_token_expires,
        )

        return schemas.JwtResponse(access_token=access_token)

    def get_current_wallet(self, token: str) -> models.WalletAuth:
        """
        Get current authenticated wallet
        """
        token_data = self.verify_token(token)
        wallet_auth = (
            self.db.query(models.WalletAuth)
            .filter(models.WalletAuth.wallet_address == token_data.wallet_address)
            .first()
        )

        if wallet_auth is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Wallet not found"
            )
        return wallet_auth
