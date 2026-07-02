"""Monitor runs 与 WebIntel reports 表。"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003_monitor_webintel"
down_revision: Union[str, None] = "002_materials_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "geo_monitor_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("status", sa.String(30), server_default="pending", nullable=False),
        sa.Column("platform", sa.String(50), server_default="all"),
        sa.Column("question_count", sa.Integer(), server_default="0"),
        sa.Column("probe_count", sa.Integer(), server_default="0"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "geo_web_insight_reports",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(255), server_default=""),
        sa.Column("status", sa.String(30), server_default="draft"),
        sa.Column("source_ids", sa.JSON(), server_default="[]"),
        sa.Column("content", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "url_import_jobs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("target", sa.String(30), server_default="knowledge"),
        sa.Column("library_id", sa.BigInteger(), nullable=True),
        sa.Column("name", sa.String(255), server_default=""),
        sa.Column("status", sa.String(30), server_default="queued"),
        sa.Column("error_message", sa.Text(), server_default=""),
        sa.Column("result_summary", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("url_import_jobs")
    op.drop_table("geo_web_insight_reports")
    op.drop_table("geo_monitor_runs")
