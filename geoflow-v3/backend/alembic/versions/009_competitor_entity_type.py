"""竞品表增加 entity_type，区分品牌与产品对标项。"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "009_competitor_entity_type"
down_revision: Union[str, None] = "008_tjg_enrichment"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "geo_monitor_competitors",
        sa.Column("entity_type", sa.String(20), server_default="brand", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("geo_monitor_competitors", "entity_type")
