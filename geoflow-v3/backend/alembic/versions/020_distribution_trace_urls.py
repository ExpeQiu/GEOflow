"""020 分发追踪 URL：canonical / tracked / trace_params。"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "020_distribution_trace_urls"
down_revision: Union[str, None] = "019_ai_lobster_gateway"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("article_distributions", sa.Column("canonical_url", sa.String(500), nullable=True))
    op.add_column("article_distributions", sa.Column("tracked_url", sa.String(800), nullable=True))
    op.add_column("article_distributions", sa.Column("trace_params_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("article_distributions", "trace_params_json")
    op.drop_column("article_distributions", "tracked_url")
    op.drop_column("article_distributions", "canonical_url")
