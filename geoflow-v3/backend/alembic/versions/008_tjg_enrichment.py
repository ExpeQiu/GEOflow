"""TJG 报告富化：场景元数据 + 探针引用表。"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "008_tjg_enrichment"
down_revision: Union[str, None] = "007_aivis_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("geo_monitor_scenes", sa.Column("external_id", sa.String(64), server_default="", nullable=True))
    op.add_column("geo_monitor_scenes", sa.Column("optimization_unit_id", sa.String(64), server_default="", nullable=True))
    op.add_column("geo_monitor_scenes", sa.Column("article_count", sa.Integer(), server_default="0", nullable=True))
    op.add_column("geo_monitor_scenes", sa.Column("visibility_pct", sa.Numeric(5, 2), server_default="0", nullable=True))
    op.add_column("geo_monitor_scenes", sa.Column("node_metadata", sa.JSON(), server_default="{}", nullable=True))

    op.create_table(
        "geo_monitor_probe_citations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "probe_result_id",
            sa.BigInteger(),
            sa.ForeignKey("geo_monitor_probe_results.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(500), server_default=""),
        sa.Column("url", sa.Text(), server_default=""),
        sa.Column("position", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_probe_citations_probe_id", "geo_monitor_probe_citations", ["probe_result_id"])


def downgrade() -> None:
    op.drop_index("ix_probe_citations_probe_id", table_name="geo_monitor_probe_citations")
    op.drop_table("geo_monitor_probe_citations")
    op.drop_column("geo_monitor_scenes", "node_metadata")
    op.drop_column("geo_monitor_scenes", "visibility_pct")
    op.drop_column("geo_monitor_scenes", "article_count")
    op.drop_column("geo_monitor_scenes", "optimization_unit_id")
    op.drop_column("geo_monitor_scenes", "external_id")
