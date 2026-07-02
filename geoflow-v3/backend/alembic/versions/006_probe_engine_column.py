"""探针结果增加 engine 字段（corpus / llm）。"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006_probe_engine"
down_revision: Union[str, None] = "005_monitor_probes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "geo_monitor_probe_results",
        sa.Column("engine", sa.String(20), server_default="corpus", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("geo_monitor_probe_results", "engine")
