"""Monitor 探针结果明细表。"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005_monitor_probes"
down_revision: Union[str, None] = "004_p2_p3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "geo_monitor_probe_results",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("question_id", sa.BigInteger(), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("brand_rank", sa.Integer(), nullable=True),
        sa.Column("mentioned", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("snippet", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_probe_run_id", "geo_monitor_probe_results", ["run_id"])
    op.create_index("ix_probe_question_platform", "geo_monitor_probe_results", ["question_id", "platform"])


def downgrade() -> None:
    op.drop_index("ix_probe_question_platform", table_name="geo_monitor_probe_results")
    op.drop_index("ix_probe_run_id", table_name="geo_monitor_probe_results")
    op.drop_table("geo_monitor_probe_results")
