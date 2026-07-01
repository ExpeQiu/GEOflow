from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TechIpAsset(Base):
    __tablename__ = "tech_ip_assets"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ip_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    mind_tag: Mapped[str] = mapped_column(String(100), default="")
    ip_layer: Mapped[str] = mapped_column(String(50), default="")
    wiki_type: Mapped[str] = mapped_column(String(32), default="concept")
    wiki_slug: Mapped[str | None] = mapped_column(String(200), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    description: Mapped[str] = mapped_column(Text, default="")
    meta_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
