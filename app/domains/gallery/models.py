from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.shared.database.connection import Base


class Gallery(Base):
    __tablename__ = "galleries"

    id = Column(Integer, primary_key=True, index=True)
    wallet_address = Column(
        String(50),
        ForeignKey("wallet_auth.wallet_address"),
        unique=True,
        nullable=False,
        index=True,
    )
    name = Column(String(100), nullable=False, index=True)
    email = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    website = Column(String(500), nullable=True)
    profile_image_url = Column(String(500), nullable=True)
    file_urls = Column(Text, nullable=True)  # JSON array stored as text
    domain_id = Column(
        String(100), nullable=True, unique=True, index=True
    )  # XRPL domain ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 1:1 relationship with WalletAuth (only for GALLERY type)
    wallet_auth = relationship("WalletAuth", back_populates="gallery")
    # One-to-many relationship with Artists
    artists = relationship("Artist", back_populates="gallery")
