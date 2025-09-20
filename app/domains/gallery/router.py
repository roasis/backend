from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.domains.gallery import schemas
from app.domains.gallery.service import GalleryService
from app.shared.database.connection import get_db

router = APIRouter(prefix="/galleries", tags=["gallery"])


@router.post("/", response_model=schemas.GalleryResponse)
def create_gallery(payload: schemas.GalleryCreate, db: Session = Depends(get_db)):
    service = GalleryService(db)
    gallery = service.create_gallery(payload)
    return gallery
