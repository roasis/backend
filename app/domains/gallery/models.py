from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.shared.database.connection import Base


class Gallery(Base):
    __tablename__ = "galleries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    email = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    website = Column(String(500), nullable=True)
    file_urls = Column(Text, nullable=True)  # JSON array stored as text
    owner_wallet_address = Column(String(50), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
