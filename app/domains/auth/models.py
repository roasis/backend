from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.shared.database.connection import Base


class WalletAuth(Base):
    __tablename__ = "wallet_auth"

    id = Column(Integer, primary_key=True, index=True)
    wallet_address = Column(String(50), unique=True, index=True, nullable=False)
    last_login = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
