"""探针结果扩展：Rank v2 / Citation 证据级字段。"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "013_probe_parser_v2"
down_revision: Union[str, None] = "012_closed_loop_remediation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "geo_monitor_probe_results",
        sa.Column("rank_method", sa.String(32), server_default="unknown", nullable=True),
    )
    op.add_column(
        "geo_monitor_probe_results",
        sa.Column("evidence_level", sa.String(8), server_default="L0", nullable=True),
    )
    op.add_column(
        "geo_monitor_probe_results",
        sa.Column("match_type", sa.String(32), server_default="none", nullable=True),
    )
    op.add_column(
        "geo_monitor_probe_results",
        sa.Column("parser_version", sa.String(16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("geo_monitor_probe_results", "parser_version")
    op.drop_column("geo_monitor_probe_results", "match_type")
    op.drop_column("geo_monitor_probe_results", "evidence_level")
    op.drop_column("geo_monitor_probe_results", "rank_method")
