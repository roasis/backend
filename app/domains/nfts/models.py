from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.shared.database.connection import Base


class Artwork(Base):
    __tablename__ = "artworks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    size = Column(String(50), nullable=False)                   # 예: "2x2", "3x3"
    price_usd = Column(Integer, nullable=False)
    grid_n = Column(Integer, nullable=False)                    # 조각 분할 크기
    image_url = Column(String(500), nullable=False)             # S3/IPFS 저장 URL
    metadata_uri_base = Column(String(500), nullable=False)     # ex) ipfs://cid/meta.json
    artist_address = Column(String(128), nullable=False)        # 작가 XRPL 주소
    created_at = Column(DateTime, default=datetime.utcnow)

    nfts = relationship("NFT", back_populates="artwork")


class NFT(Base):
    __tablename__ = "nfts"

    id = Column(Integer, primary_key=True, index=True)
    artwork_id = Column(Integer, ForeignKey("artworks.id"), nullable=False)
    uri_hex = Column(String(512), nullable=False, unique=True)  # XRPL 저장된 hex URI
    nftoken_id = Column(String(128), nullable=True)  # XRPL 발급된 NFTokenID
    tx_hash = Column(String(128), nullable=True)  # 민팅 트랜잭션 해시
    owner_address = Column(String(128), nullable=False)  # 최초 소유자(민팅 계정 or 이후 이전 계정)
    status = Column(String(50), default="minted")  # minted / listed / sold
    price = Column(Integer, nullable=False)  # USD 가격 (조각별 가격)
    extra = Column(JSON, nullable=True)  # 확장용 (가격, 메타데이터 캐시 등)

    artwork = relationship("Artwork", back_populates="nfts")
