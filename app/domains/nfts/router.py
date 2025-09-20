from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.shared.database.connection import get_db

from .schemas import RegisterMintOut, VerifyIn, VerifyOut
from .services import register_to_ipfs_and_mint, verify_tx

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
            artist_address=artist_address,
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
