from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("categories.id"), nullable=False)
    author_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("authors.id"), nullable=False)
    task_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    original_keyword: Mapped[str] = mapped_column(String(200), default="")
    keywords: Mapped[str] = mapped_column(Text, default="")
    meta_description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    review_status: Mapped[str] = mapped_column(String(20), default="pending")
    eval_status: Mapped[str] = mapped_column(String(32), default="skipped")
    eval_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    content_format: Mapped[str | None] = mapped_column(String(32), default="article")
    wiki_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    is_ai_generated: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
