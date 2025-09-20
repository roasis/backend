from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
import logging

from app.shared.database.connection import get_db
from app.domains.auth.models import UserType, WalletAuth
from app.domains.auth.router import get_current_wallet_auth

from .schemas import RegisterMintOut, VerifyIn, VerifyOut
from .services import register_to_ipfs_and_mint, verify_tx

from fastapi.security import HTTPBearer

security = HTTPBearer()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/nfts", tags=["NFTs"])


@router.get("/_ping")
def ping():
    return {"ok": True}


# @router.post("/artworks/mint", response_model=MintServerOut)
# def create_artwork_and_mint(body: MintServerIn, db: Session = Depends(get_db)):
#     try:
#         res = server_batch_mint(db, body)
#         return MintServerOut(**res)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


@router.post("/artworks/register-mint", response_model=RegisterMintOut)
async def register_and_mint(
    current_wallet: WalletAuth = Depends(get_current_wallet_auth),
    db: Session = Depends(get_db),
    # 파일
    image: UploadFile = File(..., description="작품 이미지 파일 (png/jpg)"),
    # 메타데이터 기본
    title: str = Form(...),
    description: str = Form(...),
    year: str = Form(...),
    size: str = Form(...),
    medium: str = Form(...),
    # 작품/민팅 옵션
    price_usd: int = Form(...),
    grid_n: int = Form(...),  # 2,3,4...
    artist_address: str = Form(...),
    # XRPL 옵션(기본값 예시)
    flags: int = Form(9),  # Burnable(1)+Transferable(8)=9
    transfer_fee: int = Form(0),
    taxon: int = Form(0),
):
    try:

        # 1. 작가 권한 확인
        if current_wallet.user_type != UserType.USER:
            logger.warning(f"Non-artist user {current_wallet.wallet_address} attempted to mint")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "ARTIST_ONLY",
                    "message": "Only artists (USER type) can mint artworks.",
                    "user_type": current_wallet.user_type.value
                }
            )

        # 2. 활성 계정 확인
        if not current_wallet.is_active:
            logger.warning(f"Inactive user {current_wallet.wallet_address} attempted to mint")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "ACCOUNT_INACTIVE",
                    "message": "Your account is inactive. Please contact support."
                }
            )

        # wallet_address = "rnx6G9kHEoyq12rwSQc6t5zgJ22dxFpndW"

        image_bytes = await image.read()
        result = await register_to_ipfs_and_mint(
            db,
            image_bytes=image_bytes,
            image_filename=image.filename or "artwork.png",
            title=title,
            description=description,
            year=year,
            size_label=size,
            medium=medium,
            price_usd=price_usd,
            grid_n=grid_n,
            artist_address=current_wallet.wallet_address,
            # artist_address=wallet_address,
            flags=flags,
            transfer_fee=transfer_fee,
            taxon=taxon,
        )
        return RegisterMintOut(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tx/verify", response_model=VerifyOut)
def verify(body: VerifyIn):
    try:
        return VerifyOut(**verify_tx(body.tx_hash))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
