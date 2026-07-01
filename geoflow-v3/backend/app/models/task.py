from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    title_library_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    image_library_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    image_count: Mapped[int] = mapped_column(Integer, default=1)
    prompt_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    ai_model_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    author_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    need_review: Mapped[int] = mapped_column(Integer, default=1)
    publish_interval: Mapped[int] = mapped_column(Integer, default=3600)
    author_type: Mapped[str] = mapped_column(String(20), default="random")
    custom_author_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    auto_keywords: Mapped[int] = mapped_column(Integer, default=1)
    auto_description: Mapped[int] = mapped_column(Integer, default=1)
    draft_limit: Mapped[int] = mapped_column(Integer, default=10)
    article_limit: Mapped[int] = mapped_column(Integer, default=10)
    is_loop: Mapped[int] = mapped_column(Integer, default=0)
    model_selection_mode: Mapped[str] = mapped_column(String(20), default="fixed")
    content_pipeline_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    content_format: Mapped[str | None] = mapped_column(String(32), default="article")
    wiki_page_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tech_ip_asset_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    publish_scope: Mapped[str | None] = mapped_column(String(32), default="local_and_distribution")
    created_count: Mapped[int] = mapped_column(Integer, default=0)
    published_count: Mapped[int] = mapped_column(Integer, default=0)
    loop_count: Mapped[int] = mapped_column(Integer, default=0)
    knowledge_base_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    insight_template_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    category_mode: Mapped[str] = mapped_column(String(20), default="smart")
    fixed_category_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_publish_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error_message: Mapped[str] = mapped_column(Text, default="")
    schedule_enabled: Mapped[int] = mapped_column(Integer, default=1)
    max_retry_count: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    def is_wiki_mdx(self) -> bool:
        return (self.content_format or "article") == "wiki_mdx"


class TaskRun(Base):
    __tablename__ = "task_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    article_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, default="")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    meta: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
