"""分发引用索引缓存表 — 监测扫描后自动刷新匹配结果。"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "011_distribution_citation_cache"
down_revision: Union[str, None] = "010_competitor_entity_backfill"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "distribution_citation_index",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("article_id", sa.BigInteger(), sa.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("index_status", sa.String(32), server_default="pending_scan"),
        sa.Column("citation_count", sa.Integer(), server_default="0"),
        sa.Column("scene_question_count", sa.Integer(), server_default="0"),
        sa.Column("primary_url", sa.String(500), nullable=True),
        sa.Column("platforms_json", sa.JSON(), server_default="[]"),
        sa.Column("match_types_json", sa.JSON(), server_default="[]"),
        sa.Column("citations_json", sa.JSON(), server_default="[]"),
        sa.Column("distributions_json", sa.JSON(), server_default="[]"),
        sa.Column("last_matched_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("article_id"),
    )
    op.create_index("ix_dist_citation_index_status", "distribution_citation_index", ["index_status"])

    op.create_table(
        "distribution_citation_snapshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("distributed_count", sa.Integer(), server_default="0"),
        sa.Column("indexed_count", sa.Integer(), server_default="0"),
        sa.Column("not_indexed_count", sa.Integer(), server_default="0"),
        sa.Column("pending_scan_count", sa.Integer(), server_default="0"),
        sa.Column("citation_source_count", sa.Integer(), server_default="0"),
        sa.Column("visibility_pct", sa.Numeric(6, 2), server_default="0"),
        sa.Column("positive_rate_pct", sa.Numeric(6, 2), nullable=True),
        sa.Column("monitored_questions", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_date"),
    )


def downgrade() -> None:
    op.drop_table("distribution_citation_snapshots")
    op.drop_index("ix_dist_citation_index_status", table_name="distribution_citation_index")
    op.drop_table("distribution_citation_index")
