from typing import List, Optional

from sqlalchemy.orm import Session

from app.domains.gallery import models, schemas


class GalleryService:
    def __init__(self, db: Session):
        self.db = db

    def create_gallery(self, payload: schemas.GalleryCreate) -> models.Gallery:
        gallery = models.Gallery(
            name=payload.name,
            phone=payload.phone,
            location=payload.location,
            description=payload.description,
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
        self, gallery_id: int, payload: schemas.GalleryUpdate
    ) -> Optional[models.Gallery]:
        gallery = self.get_gallery(gallery_id)
        if not gallery:
            return None
        # Apply only provided fields
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(gallery, field, value)
        self.db.add(gallery)
        self.db.commit()
        self.db.refresh(gallery)
        return gallery

    def delete_gallery(self, gallery_id: int) -> bool:
        gallery = self.get_gallery(gallery_id)
        if not gallery:
            return False
        self.db.delete(gallery)
        self.db.commit()
        return True
