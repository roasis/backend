from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.shared.database.connection import Base


class Gallery(Base):
    __tablename__ = "galleries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    phone = Column(String(30), nullable=True)
    location = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
