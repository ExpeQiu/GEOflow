"""北极星 KPI：题型 intent_type + snapshot TopN 字段 + remediation Top3。"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "014_kpi_north_star"
down_revision: Union[str, None] = "013_probe_parser_v2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "geo_monitor_questions",
        sa.Column("intent_type", sa.String(32), server_default="cognition", nullable=True),
    )
    op.add_column(
        "geo_monitor_snapshots",
        sa.Column("top1_pct", sa.Float(), nullable=True),
    )
    op.add_column(
        "geo_monitor_snapshots",
        sa.Column("top3_pct", sa.Float(), nullable=True),
    )
    op.add_column(
        "geo_monitor_snapshots",
        sa.Column("top5_pct", sa.Float(), nullable=True),
    )
    op.add_column(
        "geo_monitor_snapshots",
        sa.Column("gap_vs_leader_top3_pp", sa.Float(), nullable=True),
    )
    op.add_column(
        "geo_monitor_snapshots",
        sa.Column("mention_rate_pct", sa.Float(), nullable=True),
    )
    op.add_column(
        "geo_monitor_snapshots",
        sa.Column("sentiment_negative_pct", sa.Float(), nullable=True),
    )
    op.add_column(
        "geo_monitor_snapshots",
        sa.Column("kpi_track", sa.String(32), server_default="open_api", nullable=True),
    )
    op.add_column(
        "geo_monitor_snapshots",
        sa.Column("north_star_meta", sa.JSON(), nullable=True),
    )

    op.add_column(
        "geo_gap_remediation_runs",
        sa.Column("baseline_top3_pct", sa.Float(), nullable=True),
    )
    op.add_column(
        "geo_gap_remediation_runs",
        sa.Column("post_top3_pct", sa.Float(), nullable=True),
    )
    op.add_column(
        "geo_gap_remediation_runs",
        sa.Column("delta_top3_pp", sa.Float(), nullable=True),
    )

    # 销售口径 SSOT（Wave E 提前建表，避免后续二次迁移）
    op.create_table(
        "geo_sales_copy_assets",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("copy_type", sa.String(32), nullable=False, server_default="talking_point"),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("scene_id", sa.BigInteger(), nullable=True),
        sa.Column("tech_ip_asset_id", sa.BigInteger(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )


def downgrade() -> None:
    op.drop_table("geo_sales_copy_assets")
    op.drop_column("geo_gap_remediation_runs", "delta_top3_pp")
    op.drop_column("geo_gap_remediation_runs", "post_top3_pct")
    op.drop_column("geo_gap_remediation_runs", "baseline_top3_pct")
    op.drop_column("geo_monitor_snapshots", "north_star_meta")
    op.drop_column("geo_monitor_snapshots", "kpi_track")
    op.drop_column("geo_monitor_snapshots", "sentiment_negative_pct")
    op.drop_column("geo_monitor_snapshots", "mention_rate_pct")
    op.drop_column("geo_monitor_snapshots", "gap_vs_leader_top3_pp")
    op.drop_column("geo_monitor_snapshots", "top5_pct")
    op.drop_column("geo_monitor_snapshots", "top3_pct")
    op.drop_column("geo_monitor_snapshots", "top1_pct")
    op.drop_column("geo_monitor_questions", "intent_type")
