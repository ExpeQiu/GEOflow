"""缺口补缺实验表 — 支撑 Task→发布→再扫 lift 闭环。"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "012_closed_loop_remediation"
down_revision: Union[str, None] = "011_distribution_citation_cache"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "geo_gap_remediation_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("scene_id", sa.BigInteger(), nullable=False),
        sa.Column("task_id", sa.BigInteger(), sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(32), server_default="pending_publish", nullable=False),
        sa.Column("gap_rate_at_create", sa.Numeric(6, 3), server_default="0"),
        sa.Column("baseline_visibility_pct", sa.Numeric(6, 2), nullable=True),
        sa.Column("baseline_run_id", sa.BigInteger(), nullable=True),
        sa.Column("article_ids", sa.JSON(), server_default="[]"),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("rescan_after", sa.DateTime(), nullable=True),
        sa.Column("post_visibility_pct", sa.Numeric(6, 2), nullable=True),
        sa.Column("post_run_id", sa.BigInteger(), nullable=True),
        sa.Column("delta_visibility_pct", sa.Numeric(6, 2), nullable=True),
        sa.Column("meta", sa.JSON(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gap_remediation_status_rescan", "geo_gap_remediation_runs", ["status", "rescan_after"])
    op.create_index("ix_gap_remediation_scene", "geo_gap_remediation_runs", ["scene_id"])
    op.create_index("ix_gap_remediation_task", "geo_gap_remediation_runs", ["task_id"])


def downgrade() -> None:
    op.drop_index("ix_gap_remediation_task", table_name="geo_gap_remediation_runs")
    op.drop_index("ix_gap_remediation_scene", table_name="geo_gap_remediation_runs")
    op.drop_index("ix_gap_remediation_status_rescan", table_name="geo_gap_remediation_runs")
    op.drop_table("geo_gap_remediation_runs")
