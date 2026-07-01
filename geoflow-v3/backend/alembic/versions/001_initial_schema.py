"""初始 schema：pgvector + v3 扩展表。"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "admins",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("password", sa.String(255), nullable=False),
        sa.Column("email", sa.String(100), server_default=""),
        sa.Column("display_name", sa.String(100), server_default=""),
        sa.Column("role", sa.String(20), server_default="admin"),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("last_login", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )

    op.create_table(
        "api_access_tokens",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("admin_id", sa.BigInteger(), sa.ForeignKey("admins.id"), nullable=False),
        sa.Column("name", sa.String(100), server_default="default"),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("token_prefix", sa.String(20), nullable=False),
        sa.Column("scopes", sa.JSON(), server_default="[]"),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_access_tokens_prefix", "api_access_tokens", ["token_prefix"])

    op.create_table(
        "ai_models",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("version", sa.String(50), server_default=""),
        sa.Column("api_key", sa.String(500), nullable=False),
        sa.Column("model_id", sa.String(100), nullable=False),
        sa.Column("model_type", sa.String(20), server_default="chat"),
        sa.Column("api_url", sa.String(500), server_default="https://api.openai.com/v1"),
        sa.Column("failover_priority", sa.Integer(), server_default="100"),
        sa.Column("daily_limit", sa.Integer(), server_default="0"),
        sa.Column("used_today", sa.Integer(), server_default="0"),
        sa.Column("total_used", sa.Integer(), server_default="0"),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "prompts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("variables", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "categories",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "authors",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("bio", sa.Text(), server_default=""),
        sa.Column("email", sa.String(100), server_default=""),
        sa.Column("avatar", sa.String(200), server_default=""),
        sa.Column("website", sa.String(200), server_default=""),
        sa.Column("social_links", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "knowledge_bases",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("character_count", sa.Integer(), server_default="0"),
        sa.Column("used_task_count", sa.Integer(), server_default="0"),
        sa.Column("file_type", sa.String(20), server_default="markdown"),
        sa.Column("file_path", sa.String(500), server_default=""),
        sa.Column("word_count", sa.Integer(), server_default="0"),
        sa.Column("usage_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("knowledge_base_id", sa.BigInteger(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), server_default=""),
        sa.Column("token_count", sa.Integer(), server_default="0"),
        sa.Column("embedding_json", sa.Text(), server_default=""),
        sa.Column("embedding_model_id", sa.Integer(), nullable=True),
        sa.Column("embedding_dimensions", sa.Integer(), server_default="0"),
        sa.Column("embedding_provider", sa.String(255), server_default=""),
        sa.Column("embedding_vector", Vector(3072), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("knowledge_base_id", "chunk_index"),
    )

    op.create_table(
        "tasks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("title_library_id", sa.BigInteger(), nullable=False),
        sa.Column("image_library_id", sa.BigInteger(), nullable=True),
        sa.Column("image_count", sa.Integer(), server_default="1"),
        sa.Column("prompt_id", sa.BigInteger(), nullable=False),
        sa.Column("ai_model_id", sa.BigInteger(), nullable=False),
        sa.Column("author_id", sa.BigInteger(), nullable=True),
        sa.Column("need_review", sa.Integer(), server_default="1"),
        sa.Column("publish_interval", sa.Integer(), server_default="3600"),
        sa.Column("author_type", sa.String(20), server_default="random"),
        sa.Column("custom_author_id", sa.BigInteger(), nullable=True),
        sa.Column("auto_keywords", sa.Integer(), server_default="1"),
        sa.Column("auto_description", sa.Integer(), server_default="1"),
        sa.Column("draft_limit", sa.Integer(), server_default="10"),
        sa.Column("article_limit", sa.Integer(), server_default="10"),
        sa.Column("is_loop", sa.Integer(), server_default="0"),
        sa.Column("model_selection_mode", sa.String(20), server_default="fixed"),
        sa.Column("content_pipeline_mode", sa.String(32), nullable=True),
        sa.Column("content_format", sa.String(32), server_default="article"),
        sa.Column("wiki_page_type", sa.String(32), nullable=True),
        sa.Column("tech_ip_asset_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("publish_scope", sa.String(32), server_default="local_and_distribution"),
        sa.Column("created_count", sa.Integer(), server_default="0"),
        sa.Column("published_count", sa.Integer(), server_default="0"),
        sa.Column("loop_count", sa.Integer(), server_default="0"),
        sa.Column("knowledge_base_id", sa.BigInteger(), nullable=True),
        sa.Column("insight_template_id", sa.BigInteger(), nullable=True),
        sa.Column("category_mode", sa.String(20), server_default="smart"),
        sa.Column("fixed_category_id", sa.BigInteger(), nullable=True),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("next_run_at", sa.DateTime(), nullable=True),
        sa.Column("next_publish_at", sa.DateTime(), nullable=True),
        sa.Column("last_success_at", sa.DateTime(), nullable=True),
        sa.Column("last_error_at", sa.DateTime(), nullable=True),
        sa.Column("last_error_message", sa.Text(), server_default=""),
        sa.Column("schedule_enabled", sa.Integer(), server_default="1"),
        sa.Column("max_retry_count", sa.Integer(), server_default="3"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "articles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("slug", sa.String(500), nullable=False),
        sa.Column("excerpt", sa.Text(), server_default=""),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("category_id", sa.BigInteger(), sa.ForeignKey("categories.id"), nullable=False),
        sa.Column("author_id", sa.BigInteger(), sa.ForeignKey("authors.id"), nullable=False),
        sa.Column("task_id", sa.BigInteger(), sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("original_keyword", sa.String(200), server_default=""),
        sa.Column("keywords", sa.Text(), server_default=""),
        sa.Column("meta_description", sa.Text(), server_default=""),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("review_status", sa.String(20), server_default="pending"),
        sa.Column("eval_status", sa.String(32), server_default="skipped"),
        sa.Column("eval_meta", sa.JSON(), nullable=True),
        sa.Column("content_format", sa.String(32), server_default="article"),
        sa.Column("wiki_meta", sa.JSON(), nullable=True),
        sa.Column("view_count", sa.Integer(), server_default="0"),
        sa.Column("is_ai_generated", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "task_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.BigInteger(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("article_id", sa.BigInteger(), nullable=True),
        sa.Column("error_message", sa.Text(), server_default=""),
        sa.Column("duration_ms", sa.Integer(), server_default="0"),
        sa.Column("meta", sa.Text(), server_default=""),
        sa.Column("started_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "distribution_channels",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("channel_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "article_distributions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("article_id", sa.BigInteger(), sa.ForeignKey("articles.id", ondelete="CASCADE")),
        sa.Column("channel_id", sa.BigInteger(), sa.ForeignKey("distribution_channels.id")),
        sa.Column("status", sa.String(32), server_default="pending"),
        sa.Column("remote_id", sa.String(255), nullable=True),
        sa.Column("remote_url", sa.String(500), nullable=True),
        sa.Column("error_message", sa.Text(), server_default=""),
        sa.Column("attempt_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "article_evaluations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("article_id", sa.BigInteger(), sa.ForeignKey("articles.id", ondelete="CASCADE")),
        sa.Column("task_run_id", sa.BigInteger(), nullable=True),
        sa.Column("idempotency_key", sa.String(191), nullable=False),
        sa.Column("eval_type", sa.String(32), server_default="simulation"),
        sa.Column("status", sa.String(32), server_default="pending_eval"),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("failure_reason", sa.String(500), nullable=True),
        sa.Column("raw_response", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "insight_templates",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("style_guide", sa.JSON(), nullable=True),
        sa.Column("features", sa.JSON(), nullable=True),
        sa.Column("eeat_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("created_by_admin_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "tech_ip_assets",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ip_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("mind_tag", sa.String(100), server_default=""),
        sa.Column("ip_layer", sa.String(50), server_default=""),
        sa.Column("wiki_type", sa.String(32), server_default="concept"),
        sa.Column("wiki_slug", sa.String(200), nullable=True),
        sa.Column("priority", sa.Integer(), server_default="100"),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("meta_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ip_id"),
    )

    op.create_table(
        "api_idempotency_keys",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("idempotency_key", sa.String(120), nullable=False),
        sa.Column("route_key", sa.String(120), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("response_body", sa.Text(), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", "route_key"),
    )


def downgrade() -> None:
    for table in [
        "api_idempotency_keys",
        "tech_ip_assets",
        "insight_templates",
        "article_evaluations",
        "article_distributions",
        "distribution_channels",
        "task_runs",
        "articles",
        "tasks",
        "knowledge_chunks",
        "knowledge_bases",
        "authors",
        "categories",
        "prompts",
        "ai_models",
        "api_access_tokens",
        "admins",
    ]:
        op.drop_table(table)
