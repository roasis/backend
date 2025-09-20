import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.shared.database.connection import Base


class UserType(enum.Enum):
    USER = "USER"
    GALLERY = "GALLERY"


class WalletAuth(Base):
    __tablename__ = "wallet_auth"

    id = Column(Integer, primary_key=True, index=True)
    wallet_address = Column(String(50), unique=True, index=True, nullable=False)
    user_type = Column(Enum(UserType), nullable=False, default=UserType.USER)
    last_login = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 1:1 relationship with Artist (only for USER type)
    artist = relationship("Artist", back_populates="wallet_auth", uselist=False)

    # 1:1 relationship with Gallery (only for GALLERY type)
    gallery = relationship("Gallery", back_populates="wallet_auth", uselist=False)
