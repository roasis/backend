from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.domains.gallery import schemas
from app.domains.gallery.service import GalleryService
from app.shared.database.connection import get_db

router = APIRouter(prefix="/galleries", tags=["gallery"])


@router.post(
    "/", response_model=schemas.GalleryResponse, status_code=status.HTTP_201_CREATED
)
def create_gallery(payload: schemas.GalleryCreate, db: Session = Depends(get_db)):
    service = GalleryService(db)
    gallery = service.create_gallery(payload)
    return gallery


@router.get("/", response_model=List[schemas.GalleryResponse])
def list_galleries(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    service = GalleryService(db)
    return service.list_galleries(skip=skip, limit=limit)


@router.get("/{gallery_id}", response_model=schemas.GalleryResponse)
def get_gallery(gallery_id: int, db: Session = Depends(get_db)):
    service = GalleryService(db)
    gallery = service.get_gallery(gallery_id)
    if not gallery:
        raise HTTPException(status_code=404, detail="Gallery not found")
    return gallery


@router.put("/{gallery_id}", response_model=schemas.GalleryResponse)
def update_gallery(
    gallery_id: int,
    payload: schemas.GalleryUpdate,
    db: Session = Depends(get_db),
):
    service = GalleryService(db)
    gallery = service.update_gallery(gallery_id, payload)
    if not gallery:
        raise HTTPException(status_code=404, detail="Gallery not found")
    return gallery


@router.delete("/{gallery_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_gallery(gallery_id: int, db: Session = Depends(get_db)):
    service = GalleryService(db)
    ok = service.delete_gallery(gallery_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Gallery not found")
    return None
