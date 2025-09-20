from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.domains.artist import schemas as artist_schemas
from app.domains.auth.models import WalletAuth
from app.domains.auth.router import get_current_wallet_auth
from app.domains.gallery import schemas
from app.domains.gallery.service import GalleryService
from app.shared.database.connection import get_db

router = APIRouter(prefix="/galleries", tags=["gallery"])


@router.get("/", response_model=List[schemas.GalleryResponse])
def list_galleries(
    db: Session = Depends(get_db),
):
    service = GalleryService(db)
    return service.list_galleries()


@router.get("/me", response_model=schemas.GalleryResponse)
def get_my_gallery_profile(
    current_wallet: WalletAuth = Depends(get_current_wallet_auth),
    db: Session = Depends(get_db),
):
    """
    Get current user's gallery profile

    **Possible errors:**
    - 404: Gallery profile not found
    """
    service = GalleryService(db)
    gallery = service.get_gallery_by_wallet(current_wallet.wallet_address)
    if not gallery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gallery profile not found"
        )
    return gallery


@router.get("/{gallery_id}", response_model=schemas.GalleryResponse)
def get_gallery(
    gallery_id: int,
    db: Session = Depends(get_db),
):
    service = GalleryService(db)
    gallery = service.get_gallery(gallery_id)
    if not gallery:
        raise HTTPException(status_code=404, detail="Gallery not found")
    return gallery


@router.put("/{gallery_id}", response_model=schemas.GalleryResponse)
def update_gallery(
    gallery_id: int,
    payload: schemas.GalleryUpdate,
    current_wallet: WalletAuth = Depends(get_current_wallet_auth),
    db: Session = Depends(get_db),
):
    service = GalleryService(db)
    gallery = service.update_gallery(gallery_id, payload, current_wallet.wallet_address)
    if not gallery:
        raise HTTPException(status_code=404, detail="Gallery not found")
    return gallery


@router.delete("/{gallery_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_gallery(
    gallery_id: int,
    current_wallet: WalletAuth = Depends(get_current_wallet_auth),
    db: Session = Depends(get_db),
):
    service = GalleryService(db)
    ok = service.delete_gallery(gallery_id, current_wallet.wallet_address)
    if not ok:
        raise HTTPException(status_code=404, detail="Gallery not found")
    return None


@router.post("/invite-artist", response_model=artist_schemas.ArtistInviteResponse)
def invite_artist(
    payload: artist_schemas.ArtistInviteRequest,
    current_wallet: WalletAuth = Depends(get_current_wallet_auth),
    db: Session = Depends(get_db),
):
    """
    Invite an artist to the gallery

    **Requirements:**
    - Current user must be a gallery owner
    - Artist must exist and not be already assigned to a gallery

    **Possible errors:**
    - 404: Gallery or Artist not found
    - 400: Artist already belongs to a gallery
    - 403: Only gallery owner can invite artists
    """
    service = GalleryService(db)
    result = service.invite_artist(payload.artist_wallet_address, current_wallet.wallet_address)
    return result


@router.get("/my/artists", response_model=List[artist_schemas.ArtistResponse])
def get_my_gallery_artists(
    current_wallet: WalletAuth = Depends(get_current_wallet_auth),
    db: Session = Depends(get_db),
):
    """
    Get all artists belonging to current gallery

    **Possible errors:**
    - 404: Gallery not found
    """
    service = GalleryService(db)
    artists = service.get_gallery_artists(current_wallet.wallet_address)
    return artists


@router.delete("/remove-artist/{artist_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_artist_from_gallery(
    artist_id: int,
    current_wallet: WalletAuth = Depends(get_current_wallet_auth),
    db: Session = Depends(get_db),
):
    """
    Remove an artist from the gallery

    **Possible errors:**
    - 404: Gallery or Artist not found
    - 403: Only gallery owner can remove artists
    - 400: Artist does not belong to this gallery
    """
    service = GalleryService(db)
    success = service.remove_artist(artist_id, current_wallet.wallet_address)
    if not success:
        raise HTTPException(status_code=404, detail="Artist not found or not in this gallery")
    return None
