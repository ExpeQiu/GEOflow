"""019 AI 模型接入 Lobster 网关：vendor + connection_kind。"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "019_ai_lobster_gateway"
down_revision: Union[str, None] = "018_probe_scheme_tracks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ai_models", sa.Column("vendor", sa.String(40), server_default="", nullable=True))
    op.add_column(
        "ai_models",
        sa.Column("connection_kind", sa.String(20), server_default="inherit", nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ai_models", "connection_kind")
    op.drop_column("ai_models", "vendor")
