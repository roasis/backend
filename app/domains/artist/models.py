from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.shared.database.connection import Base


class Artist(Base):
    __tablename__ = "artists"

    id = Column(Integer, primary_key=True, index=True)
    wallet_address = Column(
        String(50),
        ForeignKey("wallet_auth.wallet_address"),
        unique=True,
        nullable=False,
        index=True,
    )
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=True)
    profile_image_url = Column(String(500), nullable=True)
    gallery_id = Column(Integer, ForeignKey("galleries.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 1:1 relationship with WalletAuth
    wallet_auth = relationship("WalletAuth", back_populates="artist")
    # Many-to-one relationship with Gallery
    gallery = relationship("Gallery", back_populates="artists")
