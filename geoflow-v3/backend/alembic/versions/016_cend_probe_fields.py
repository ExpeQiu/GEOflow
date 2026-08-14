"""016 C 端探针扩展：思考链路 / 结构化排名 / citations 证据级。"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "016_cend_probe_fields"
down_revision: Union[str, None] = "015_probe_gold_labels"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("geo_monitor_probe_results", sa.Column("thinking_text", sa.Text(), nullable=True))
    op.add_column("geo_monitor_probe_results", sa.Column("thinking_ms", sa.Integer(), nullable=True))
    op.add_column("geo_monitor_probe_results", sa.Column("keywords", JSONB(), server_default="[]", nullable=True))
    op.add_column("geo_monitor_probe_results", sa.Column("entities", JSONB(), server_default="[]", nullable=True))
    op.add_column("geo_monitor_probe_results", sa.Column("rank_blocks", JSONB(), server_default="[]", nullable=True))
    op.add_column("geo_monitor_probe_results", sa.Column("decision_table", JSONB(), server_default="[]", nullable=True))
    op.add_column("geo_monitor_probe_results", sa.Column("source_hosts", JSONB(), server_default="[]", nullable=True))
    op.add_column("geo_monitor_probe_results", sa.Column("capture_artifact", sa.String(512), nullable=True))
    op.add_column(
        "geo_monitor_probe_results",
        sa.Column("metric_kind", sa.String(32), server_default="mixed", nullable=True),
    )
    op.add_column("geo_monitor_probe_results", sa.Column("cend_meta", JSONB(), server_default="{}", nullable=True))

    op.add_column(
        "geo_monitor_probe_citations",
        sa.Column("evidence_level", sa.String(8), server_default="L0", nullable=True),
    )
    op.add_column(
        "geo_monitor_probe_citations",
        sa.Column("source", sa.String(32), server_default="unknown", nullable=True),
    )

    op.add_column("geo_probe_gold_labels", sa.Column("thinking_text", sa.Text(), nullable=True))
    op.add_column("geo_probe_gold_labels", sa.Column("keywords", JSONB(), server_default="[]", nullable=True))
    op.add_column("geo_probe_gold_labels", sa.Column("rank_blocks", JSONB(), server_default="[]", nullable=True))
    op.add_column("geo_probe_gold_labels", sa.Column("decision_table", JSONB(), server_default="[]", nullable=True))
    op.add_column("geo_probe_gold_labels", sa.Column("source_hosts", JSONB(), server_default="[]", nullable=True))
    op.add_column("geo_probe_gold_labels", sa.Column("capture_artifact", sa.String(512), nullable=True))
    op.add_column("geo_probe_gold_labels", sa.Column("cend_meta", JSONB(), server_default="{}", nullable=True))


def downgrade() -> None:
    for col in (
        "cend_meta",
        "capture_artifact",
        "source_hosts",
        "decision_table",
        "rank_blocks",
        "keywords",
        "thinking_text",
    ):
        op.drop_column("geo_probe_gold_labels", col)

    op.drop_column("geo_monitor_probe_citations", "source")
    op.drop_column("geo_monitor_probe_citations", "evidence_level")

    for col in (
        "cend_meta",
        "metric_kind",
        "capture_artifact",
        "source_hosts",
        "decision_table",
        "rank_blocks",
        "entities",
        "keywords",
        "thinking_ms",
        "thinking_text",
    ):
        op.drop_column("geo_monitor_probe_results", col)
