from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.domains.artwork import schemas
from app.domains.artwork.service import ArtworkService
from app.domains.auth.models import WalletAuth
from app.domains.auth.router import get_current_wallet_auth
from app.shared.database.connection import get_db

router = APIRouter(prefix="/artworks", tags=["artwork"])


@router.get("/", response_model=List[schemas.ArtworkListResponse])
def list_artworks(
    db: Session = Depends(get_db),
):
    """List all artworks"""
    service = ArtworkService(db)
    return service.list_artworks()


@router.get("/my", response_model=List[schemas.ArtworkResponse])
def get_my_artworks(
    current_wallet: WalletAuth = Depends(get_current_wallet_auth),
    db: Session = Depends(get_db),
):
    """Get current artist's artworks"""
    service = ArtworkService(db)
    return service.get_artwork_by_artist_full(current_wallet.wallet_address)


@router.get("/{artwork_id}", response_model=schemas.ArtworkResponse)
def get_artwork(
    artwork_id: int,
    db: Session = Depends(get_db),
):
    """Get artwork by ID"""
    service = ArtworkService(db)
    artwork = service.get_artwork(artwork_id)
    if not artwork:
        raise HTTPException(status_code=404, detail="Artwork not found")
    return artwork


@router.put("/{artwork_id}", response_model=schemas.ArtworkResponse)
def update_artwork(
    artwork_id: int,
    payload: schemas.ArtworkUpdateRequest,
    current_wallet: WalletAuth = Depends(get_current_wallet_auth),
    db: Session = Depends(get_db),
):
    """Update artwork (owner only)"""
    service = ArtworkService(db)
    artwork = service.update_artwork(artwork_id, payload, current_wallet.wallet_address)
    if not artwork:
        raise HTTPException(status_code=404, detail="Artwork not found")
    return artwork


@router.delete("/{artwork_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_artwork(
    artwork_id: int,
    current_wallet: WalletAuth = Depends(get_current_wallet_auth),
    db: Session = Depends(get_db),
):
    """Delete artwork (owner only)"""
    service = ArtworkService(db)
    success = service.delete_artwork(artwork_id, current_wallet.wallet_address)
    if not success:
        raise HTTPException(status_code=404, detail="Artwork not found")
    return None


@router.get("/artist/{artist_address}", response_model=List[schemas.ArtworkListResponse])
def get_artworks_by_artist(
    artist_address: str,
    db: Session = Depends(get_db),
):
    """Get artworks by specific artist"""
    service = ArtworkService(db)
    return service.get_artwork_by_artist(artist_address)
