from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.domains.artist import models, schemas
from app.domains.auth.models import UserType


class ArtistService:
    def __init__(self, db: Session):
        self.db = db

    def create_artist(
        self, payload: schemas.ArtistCreate, wallet_address: str, user_type: UserType
    ) -> models.Artist:
        # Only USER type can create artist profile
        if user_type != UserType.USER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only USER type can create artist profile",
            )

        # Check if artist profile already exists
        existing_artist = (
            self.db.query(models.Artist)
            .filter(models.Artist.wallet_address == wallet_address)
            .first()
        )

        if existing_artist:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Artist profile already exists",
            )

        artist = models.Artist(
            wallet_address=wallet_address,
            name=payload.name,
            email=payload.email,
            profile_image=payload.profile_image,
        )
        self.db.add(artist)
        self.db.commit()
        self.db.refresh(artist)
        return artist

    def get_artist(self, artist_id: int) -> Optional[models.Artist]:
        return (
            self.db.query(models.Artist).filter(models.Artist.id == artist_id).first()
        )

    def get_artist_by_wallet(self, wallet_address: str) -> Optional[models.Artist]:
        return (
            self.db.query(models.Artist)
            .filter(models.Artist.wallet_address == wallet_address)
            .first()
        )

    def list_artists(self, skip: int = 0, limit: int = 100) -> List[models.Artist]:
        return (
            self.db.query(models.Artist)
            .order_by(models.Artist.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_artist(
        self, artist_id: int, payload: schemas.ArtistUpdate, current_wallet_address: str
    ) -> Optional[models.Artist]:
        artist = self.get_artist(artist_id)
        if not artist:
            return None

        # Check if current user is the owner
        if artist.wallet_address != current_wallet_address:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only artist owner can update this profile",
            )

        # Apply only provided fields
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(artist, field, value)

        self.db.add(artist)
        self.db.commit()
        self.db.refresh(artist)
        return artist

    def delete_artist(self, artist_id: int, current_wallet_address: str) -> bool:
        artist = self.get_artist(artist_id)
        if not artist:
            return False

        # Check if current user is the owner
        if artist.wallet_address != current_wallet_address:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only artist owner can delete this profile",
            )

        self.db.delete(artist)
        self.db.commit()
        return True
