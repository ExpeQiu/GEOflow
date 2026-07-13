"""AIVIS 升级基础表：场景图谱、问题模板、竞品、快照、报告。"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007_aivis_foundation"
down_revision: Union[str, None] = "006_probe_engine"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "geo_monitor_scenes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("persona", sa.String(120), server_default=""),
        sa.Column("scene_name", sa.String(200), nullable=False),
        sa.Column("intent", sa.String(200), server_default=""),
        sa.Column("weight_pct", sa.Numeric(5, 2), server_default="0"),
        sa.Column("industry", sa.String(80), server_default=""),
        sa.Column("gap_rate", sa.Numeric(5, 3), server_default="0"),
        sa.Column("gap_priority", sa.String(20), server_default="covered"),
        sa.Column("insight_template_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("last_gap_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "geo_monitor_query_templates",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("template_type", sa.String(30), server_default="brand"),
        sa.Column("category", sa.String(80), server_default=""),
        sa.Column("pattern", sa.Text(), nullable=False),
        sa.Column("scene_id", sa.BigInteger(), sa.ForeignKey("geo_monitor_scenes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("default_priority", sa.Integer(), server_default="50"),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "geo_monitor_competitors",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("brand_name", sa.String(120), nullable=False),
        sa.Column("aliases", sa.JSON(), server_default="[]"),
        sa.Column("is_self", sa.Boolean(), server_default="false"),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "geo_monitor_snapshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("mention_rate", sa.Numeric(6, 4), server_default="0"),
        sa.Column("visibility_pct", sa.Numeric(6, 2), server_default="0"),
        sa.Column("weighted_rank_score", sa.Numeric(6, 2), server_default="0"),
        sa.Column("sentiment_score", sa.Numeric(6, 2), nullable=True),
        sa.Column("platform_matrix", sa.JSON(), server_default="[]"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_date"),
    )
    op.create_table(
        "geo_visibility_reports",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(255), server_default=""),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("sections", sa.JSON(), server_default="{}"),
        sa.Column("status", sa.String(30), server_default="draft"),
        sa.Column("html_path", sa.String(500), server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "geo_monitor_insights",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("insight_type", sa.String(40), nullable=False),
        sa.Column("title", sa.String(255), server_default=""),
        sa.Column("body", sa.Text(), server_default=""),
        sa.Column("payload", sa.JSON(), server_default="{}"),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )

    op.add_column("geo_monitor_questions", sa.Column("scene_id", sa.BigInteger(), nullable=True))
    op.add_column("geo_monitor_questions", sa.Column("template_id", sa.BigInteger(), nullable=True))
    op.add_column("geo_monitor_questions", sa.Column("query_type", sa.String(30), server_default="brand"))
    op.add_column(
        "geo_monitor_questions",
        sa.Column("competitor_brands", sa.JSON(), server_default="[]"),
    )

    op.add_column(
        "geo_monitor_probe_results",
        sa.Column("ranking_score", sa.Numeric(4, 2), server_default="0"),
    )
    op.add_column("geo_monitor_probe_results", sa.Column("sentiment", sa.JSON(), nullable=True))
    op.add_column(
        "geo_monitor_probe_results",
        sa.Column("competitor_mentions", sa.JSON(), server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("geo_monitor_probe_results", "competitor_mentions")
    op.drop_column("geo_monitor_probe_results", "sentiment")
    op.drop_column("geo_monitor_probe_results", "ranking_score")
    op.drop_column("geo_monitor_questions", "competitor_brands")
    op.drop_column("geo_monitor_questions", "query_type")
    op.drop_column("geo_monitor_questions", "template_id")
    op.drop_column("geo_monitor_questions", "scene_id")
    op.drop_table("geo_monitor_insights")
    op.drop_table("geo_visibility_reports")
    op.drop_table("geo_monitor_snapshots")
    op.drop_table("geo_monitor_competitors")
    op.drop_table("geo_monitor_query_templates")
    op.drop_table("geo_monitor_scenes")
