from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, JSON, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ArticleEvaluation(Base):
    __tablename__ = "article_evaluations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("articles.id", ondelete="CASCADE"))
    task_run_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(191), nullable=False)
    eval_type: Mapped[str] = mapped_column(String(32), default="simulation")
    status: Mapped[str] = mapped_column(String(32), default="pending_eval")
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class InsightTemplate(Base):
    __tablename__ = "insight_templates"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    style_guide: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    features: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    eeat_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    created_by_admin_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
