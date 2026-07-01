"""素材三库、站点设置、分发绑定表。"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_materials_settings"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "keyword_libraries",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("keyword_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "keywords",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("library_id", sa.BigInteger(), sa.ForeignKey("keyword_libraries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("keyword", sa.String(200), nullable=False),
        sa.Column("used_count", sa.Integer(), server_default="0"),
        sa.Column("usage_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("library_id", "keyword"),
    )
    op.create_table(
        "title_libraries",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("title_count", sa.Integer(), server_default="0"),
        sa.Column("generation_type", sa.String(20), server_default="manual"),
        sa.Column("keyword_library_id", sa.BigInteger(), sa.ForeignKey("keyword_libraries.id"), nullable=True),
        sa.Column("ai_model_id", sa.BigInteger(), sa.ForeignKey("ai_models.id"), nullable=True),
        sa.Column("prompt_id", sa.BigInteger(), sa.ForeignKey("prompts.id"), nullable=True),
        sa.Column("generation_rounds", sa.Integer(), server_default="1"),
        sa.Column("is_ai_generated", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "titles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("library_id", sa.BigInteger(), sa.ForeignKey("title_libraries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("keyword", sa.String(200), server_default=""),
        sa.Column("is_ai_generated", sa.Boolean(), server_default="false"),
        sa.Column("used_count", sa.Integer(), server_default="0"),
        sa.Column("usage_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "image_libraries",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("image_count", sa.Integer(), server_default="0"),
        sa.Column("used_task_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "images",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("library_id", sa.BigInteger(), sa.ForeignKey("image_libraries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("file_name", sa.String(255), server_default=""),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_size", sa.Integer(), server_default="0"),
        sa.Column("mime_type", sa.String(100), server_default=""),
        sa.Column("width", sa.Integer(), server_default="0"),
        sa.Column("height", sa.Integer(), server_default="0"),
        sa.Column("tags", sa.Text(), server_default=""),
        sa.Column("used_count", sa.Integer(), server_default="0"),
        sa.Column("usage_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "site_settings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("setting_key", sa.String(100), nullable=False),
        sa.Column("setting_value", sa.Text(), server_default=""),
        sa.Column("value_type", sa.String(20), server_default="string"),
        sa.Column("group_name", sa.String(50), server_default="general"),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("setting_key"),
    )
    op.create_table(
        "distribution_channel_secrets",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("channel_id", sa.BigInteger(), sa.ForeignKey("distribution_channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("secret_hash", sa.String(255), nullable=False),
        sa.Column("secret_prefix", sa.String(20), server_default=""),
        sa.Column("label", sa.String(100), server_default="default"),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("rotated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "task_distribution_channels",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.BigInteger(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel_id", sa.BigInteger(), sa.ForeignKey("distribution_channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "channel_id"),
    )
    op.create_table(
        "admin_activity_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("admin_id", sa.BigInteger(), sa.ForeignKey("admins.id"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), server_default=""),
        sa.Column("resource_id", sa.String(50), server_default=""),
        sa.Column("detail", sa.Text(), server_default=""),
        sa.Column("ip_address", sa.String(45), server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "geo_monitor_questions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("priority", sa.Integer(), server_default="50"),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("last_scan_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "geo_web_sources",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("label", sa.String(200), server_default=""),
        sa.Column("fetch_status", sa.String(32), server_default="pending"),
        sa.Column("last_fetched_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    for table in [
        "geo_web_sources",
        "geo_monitor_questions",
        "admin_activity_logs",
        "task_distribution_channels",
        "distribution_channel_secrets",
        "site_settings",
        "images",
        "image_libraries",
        "titles",
        "title_libraries",
        "keywords",
        "keyword_libraries",
    ]:
        op.drop_table(table)
