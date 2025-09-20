from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.domains.artwork import schemas
from app.domains.nfts.models import Artwork


class ArtworkService:
    def __init__(self, db: Session):
        self.db = db

    def get_artwork(self, artwork_id: int) -> Optional[dict]:
        """Get artwork by ID"""
        artwork = (
            self.db.query(Artwork)
            .filter(Artwork.id == artwork_id)
            .first()
        )
        if not artwork:
            return None
        # NFT 리스트 직렬화
        nft_list = []
        for nft in artwork.nfts:
            nft_list.append({
                "id": nft.id,
                "artwork_id": nft.artwork_id,
                "uri_hex": nft.uri_hex,
                "nftoken_id": nft.nftoken_id,
                "tx_hash": nft.tx_hash,
                "owner_address": nft.owner_address,
                "status": nft.status,
                "price": nft.price,
                "extra": nft.extra,
            })

        return {
            "id": artwork.id,
            "title": artwork.title,
            "description": artwork.description,
            "size": artwork.size,
            "price_usd": artwork.price_usd,
            "grid_n": artwork.grid_n,
            "image_url": artwork.image_url,
            "metadata_uri_base": artwork.metadata_uri_base,
            "artist_address": artwork.artist_address,
            "created_at": artwork.created_at,
            "nfts": nft_list,
        }

    def get_artwork_by_artist(self, artist_address: str) -> List[dict]:
        """Get artworks by artist (list response)"""
        artworks = (
            self.db.query(Artwork)
            .filter(Artwork.artist_address == artist_address)
            .order_by(Artwork.created_at.desc())
            .all()
        )

        return [
            {
                "id": artwork.id,
                "title": artwork.title,
                "size": artwork.size,
                "price_usd": artwork.price_usd,
                "image_url": artwork.image_url,
                "artist_address": artwork.artist_address,
                "created_at": artwork.created_at,
            }
            for artwork in artworks
        ]

    def get_artwork_by_artist_full(self, artist_address: str) -> List[dict]:
        """Get artworks by artist (full response)"""
        artworks = (
            self.db.query(Artwork)
            .filter(Artwork.artist_address == artist_address)
            .order_by(Artwork.created_at.desc())
            .all()
        )

        return [
            {
                "id": artwork.id,
                "title": artwork.title,
                "description": artwork.description,
                "size": artwork.size,
                "price_usd": artwork.price_usd,
                "grid_n": artwork.grid_n,
                "image_url": artwork.image_url,
                "metadata_uri_base": artwork.metadata_uri_base,
                "artist_address": artwork.artist_address,
                "created_at": artwork.created_at,
            }
            for artwork in artworks
        ]

    def list_artworks(self) -> List[dict]:
        """List all artworks"""
        artworks = (
            self.db.query(Artwork)
            .order_by(Artwork.created_at.desc())
            .all()
        )

        return [
            {
                "id": artwork.id,
                "title": artwork.title,
                "size": artwork.size,
                "price_usd": artwork.price_usd,
                "image_url": artwork.image_url,
                "artist_address": artwork.artist_address,
                "created_at": artwork.created_at,
            }
            for artwork in artworks
        ]

    def update_artwork(
        self,
        artwork_id: int,
        payload: schemas.ArtworkUpdateRequest,
        current_artist_address: str,
    ) -> Optional[dict]:
        """Update artwork (only by owner artist)"""
        artwork = (
            self.db.query(Artwork)
            .filter(Artwork.id == artwork_id)
            .first()
        )
        if not artwork:
            return None

        # Check if current user is the owner
        if artwork.artist_address != current_artist_address:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only artwork owner can update this artwork",
            )

        # Apply provided fields
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(artwork, field):
                setattr(artwork, field, value)

        self.db.add(artwork)
        self.db.commit()
        self.db.refresh(artwork)

        return {
            "id": artwork.id,
            "title": artwork.title,
            "description": artwork.description,
            "size": artwork.size,
            "price_usd": artwork.price_usd,
            "grid_n": artwork.grid_n,
            "image_url": artwork.image_url,
            "metadata_uri_base": artwork.metadata_uri_base,
            "artist_address": artwork.artist_address,
            "created_at": artwork.created_at,
        }

    def delete_artwork(self, artwork_id: int, current_artist_address: str) -> bool:
        """Delete artwork (only by owner artist)"""
        artwork = (
            self.db.query(Artwork)
            .filter(Artwork.id == artwork_id)
            .first()
        )
        if not artwork:
            return False

        # Check if current user is the owner
        if artwork.artist_address != current_artist_address:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only artwork owner can delete this artwork",
            )

        self.db.delete(artwork)
        self.db.commit()
        return True
