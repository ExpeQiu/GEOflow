"""018 三层探针口径：scheme / tracks / reasoning_grade / framework。"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "018_probe_scheme_tracks"
down_revision: Union[str, None] = "017_geo_themes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "geo_monitor_probe_results",
        sa.Column("scheme", sa.String(32), server_default="open_api", nullable=True),
    )
    op.add_column(
        "geo_monitor_probe_results",
        sa.Column("tracks", JSONB(), server_default='["C"]', nullable=True),
    )
    op.add_column(
        "geo_monitor_probe_results",
        sa.Column("reasoning_grade", sa.String(16), server_default="none", nullable=True),
    )
    op.add_column(
        "geo_monitor_probe_results",
        sa.Column("framework", JSONB(), server_default="{}", nullable=True),
    )


def downgrade() -> None:
    op.drop_column("geo_monitor_probe_results", "framework")
    op.drop_column("geo_monitor_probe_results", "reasoning_grade")
    op.drop_column("geo_monitor_probe_results", "tracks")
    op.drop_column("geo_monitor_probe_results", "scheme")
