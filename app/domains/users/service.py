from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.domains.users import models, schemas

class UserService:
    def __init__(self, db: Session):
        self.db = db

    def create_user(self, user: schemas.UserCreate) -> models.User:
        # Check if user already exists
        existing_user = self.db.query(models.User).filter(
            (models.User.username == user.username) | (models.User.email == user.email)
        ).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username or email already registered")
        
        # Create new user (password should be hashed in production)
        db_user = models.User(
            username=user.username,
            email=user.email,
            hashed_password=user.password  # TODO: Hash password
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def get_user_by_id(self, user_id: int) -> models.User:
        user = self.db.query(models.User).filter(models.User.id == user_id).first()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    def get_user_by_username(self, username: str) -> models.User:
        user = self.db.query(models.User).filter(models.User.username == username).first()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return user