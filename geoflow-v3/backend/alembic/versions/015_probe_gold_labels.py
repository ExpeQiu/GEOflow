"""015 probe gold labels table for PROBE-TRUTH M4."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "015_probe_gold_labels"
down_revision: Union[str, None] = "014_kpi_north_star"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "geo_probe_gold_labels",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("question_id", sa.BigInteger(), nullable=True),
        sa.Column("platform", sa.String(64), nullable=False),
        sa.Column("source", sa.String(32), server_default="manual", nullable=False),
        sa.Column("mentioned", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("brand_rank", sa.Integer(), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("cited_urls", JSONB(), server_default="[]", nullable=True),
        sa.Column("open_api_probe_id", sa.BigInteger(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_geo_probe_gold_qid_plat", "geo_probe_gold_labels", ["question_id", "platform"])


def downgrade() -> None:
    op.drop_index("ix_geo_probe_gold_qid_plat", table_name="geo_probe_gold_labels")
    op.drop_table("geo_probe_gold_labels")
