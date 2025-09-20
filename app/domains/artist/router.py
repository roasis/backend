from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.domains.artist import schemas
from app.domains.artist.service import ArtistService
from app.domains.auth.models import WalletAuth
from app.domains.auth.router import get_current_wallet_auth
from app.shared.database.connection import get_db

router = APIRouter(prefix="/artists", tags=["artist"])


@router.get("/", response_model=List[schemas.ArtistListResponse])
def list_artists(
    db: Session = Depends(get_db),
):
    """
    List all artist profiles
    """
    service = ArtistService(db)
    return service.list_artists()


@router.get("/me", response_model=schemas.ArtistResponse)
def get_my_artist_profile(
    current_wallet: WalletAuth = Depends(get_current_wallet_auth),
    db: Session = Depends(get_db),
):
    """
    Get current user's artist profile

    **Possible errors:**
    - 404: Artist profile not found
    """
    service = ArtistService(db)
    artist = service.get_artist_by_wallet(current_wallet.wallet_address)
    if not artist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Artist profile not found"
        )
    return artist


@router.get("/{artist_id}", response_model=schemas.ArtistResponse)
def get_artist(
    artist_id: int,
    db: Session = Depends(get_db),
):
    """
    Get artist profile by ID

    **Possible errors:**
    - 404: Artist not found
    """
    service = ArtistService(db)
    artist = service.get_artist(artist_id)
    if not artist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Artist not found"
        )
    return artist


@router.put("/{artist_id}", response_model=schemas.ArtistResponse)
def update_artist(
    artist_id: int,
    payload: schemas.ArtistUpdate,
    current_wallet: WalletAuth = Depends(get_current_wallet_auth),
    db: Session = Depends(get_db),
):
    """
    Update artist profile (only owner)

    **Possible errors:**
    - 403: Only artist owner can update this profile
    - 404: Artist not found
    """
    service = ArtistService(db)
    artist = service.update_artist(artist_id, payload, current_wallet.wallet_address)
    if not artist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Artist not found"
        )
    return artist


@router.delete("/{artist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_artist(
    artist_id: int,
    current_wallet: WalletAuth = Depends(get_current_wallet_auth),
    db: Session = Depends(get_db),
):
    """
    Delete artist profile (only owner)

    **Possible errors:**
    - 403: Only artist owner can delete this profile
    - 404: Artist not found
    """
    service = ArtistService(db)
    ok = service.delete_artist(artist_id, current_wallet.wallet_address)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Artist not found"
        )
    return None
