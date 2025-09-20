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
