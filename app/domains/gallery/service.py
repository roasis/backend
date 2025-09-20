import json
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.domains.gallery import models, schemas


class GalleryService:
    def __init__(self, db: Session):
        self.db = db

    def _serialize_file_urls(self, file_urls: Optional[List[str]]) -> Optional[str]:
        """Convert list of URLs to JSON string"""
        if file_urls is None:
            return None
        return json.dumps(file_urls)

    def _deserialize_file_urls(
        self, file_urls_json: Optional[str]
    ) -> Optional[List[str]]:
        """Convert JSON string to list of URLs"""
        if file_urls_json is None:
            return None
        try:
            return json.loads(file_urls_json)
        except (json.JSONDecodeError, TypeError):
            return None

    def create_gallery(
        self, payload: schemas.GalleryCreate, owner_wallet_address: str
    ) -> models.Gallery:
        gallery = models.Gallery(
            name=payload.name,
            email=payload.email,
            description=payload.description,
            website=payload.website,
            file_urls=self._serialize_file_urls(payload.file_urls),
            owner_wallet_address=owner_wallet_address,
        )
        self.db.add(gallery)
        self.db.commit()
        self.db.refresh(gallery)
        return gallery

    def get_gallery(self, gallery_id: int) -> Optional[models.Gallery]:
        return (
            self.db.query(models.Gallery)
            .filter(models.Gallery.id == gallery_id)
            .first()
        )

    def list_galleries(self, skip: int = 0, limit: int = 100) -> List[models.Gallery]:
        return (
            self.db.query(models.Gallery)
            .order_by(models.Gallery.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_gallery(
        self,
        gallery_id: int,
        payload: schemas.GalleryUpdate,
        current_wallet_address: str,
    ) -> Optional[models.Gallery]:
        gallery = self.get_gallery(gallery_id)
        if not gallery:
            return None

        # Check if current user is the owner
        if gallery.owner_wallet_address != current_wallet_address:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only gallery owner can update this gallery",
            )

        # Apply only provided fields
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "file_urls":
                # Serialize file URLs to JSON
                setattr(gallery, field, self._serialize_file_urls(value))
            else:
                setattr(gallery, field, value)
        self.db.add(gallery)
        self.db.commit()
        self.db.refresh(gallery)
        return gallery

    def delete_gallery(self, gallery_id: int, current_wallet_address: str) -> bool:
        gallery = self.get_gallery(gallery_id)
        if not gallery:
            return False

        # Check if current user is the owner
        if gallery.owner_wallet_address != current_wallet_address:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only gallery owner can delete this gallery",
            )

        self.db.delete(gallery)
        self.db.commit()
        return True
