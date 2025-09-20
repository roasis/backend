from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.domains.users import schemas
from app.domains.users.service import UserService
from app.shared.database.connection import get_db

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    user_service = UserService(db)
    return user_service.create_user(user)


@router.get("/{user_id}", response_model=schemas.UserResponse)
def read_user(user_id: int, db: Session = Depends(get_db)):
    user_service = UserService(db)
    return user_service.get_user_by_id(user_id)


@router.get("/username/{username}", response_model=schemas.UserResponse)
def read_user_by_username(username: str, db: Session = Depends(get_db)):
    user_service = UserService(db)
    return user_service.get_user_by_username(username)
