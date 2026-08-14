"""Theme（主题包）— 贯穿 L1→L2→L3→GEOweb 的一等公民。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

THEME_STATUSES = (
    "draft",
    "confirmed",
    "producing",
    "gate_passed",
    "distributing",
    "published",
    "measuring",
    "completed",
)

DEFAULT_PACK_SPEC = [
    {"type": "topic", "title": "", "role": "hub", "required": True},
    {"type": "concept", "title": "", "role": "definition", "required": True},
    {"type": "compare", "title": "", "role": "decision", "required": True},
    {"type": "guide", "title": "", "role": "howto", "required": True},
    {"type": "article", "title": "", "role": "narrative", "required": False},
]


class GeoTheme(Base):
    __tablename__ = "geo_themes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    scene_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    domain: Mapped[str | None] = mapped_column(String(32), nullable=True)
    gate_mode: Mapped[str] = mapped_column(String(16), default="soft")
    target_queries: Mapped[list | None] = mapped_column(JSON, nullable=True)
    pack_spec: Mapped[list | None] = mapped_column(JSON, nullable=True)
    knowledge_base_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    insight_template_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    prompt_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    ai_model_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    title_library_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    task_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    remediation_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    gate_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    geoweb_hub_slug: Mapped[str | None] = mapped_column(String(200), nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
