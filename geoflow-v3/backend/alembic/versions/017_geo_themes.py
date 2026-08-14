"""Theme 主题包主链路：geo_themes + articles/remediation theme_id。"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "017_geo_themes"
down_revision: Union[str, None] = "016_cend_probe_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "geo_themes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(200), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("scene_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(32), server_default="draft", nullable=False),
        sa.Column("domain", sa.String(32), nullable=True),
        sa.Column("gate_mode", sa.String(16), server_default="soft", nullable=False),
        sa.Column("target_queries", sa.JSON(), server_default="[]"),
        sa.Column("pack_spec", sa.JSON(), server_default="[]"),
        sa.Column("knowledge_base_id", sa.BigInteger(), nullable=True),
        sa.Column("insight_template_id", sa.BigInteger(), nullable=True),
        sa.Column("prompt_id", sa.BigInteger(), nullable=True),
        sa.Column("ai_model_id", sa.BigInteger(), nullable=True),
        sa.Column("title_library_id", sa.BigInteger(), nullable=True),
        sa.Column("task_id", sa.BigInteger(), sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("remediation_id", sa.BigInteger(), nullable=True),
        sa.Column("gate_summary", sa.JSON(), server_default="{}"),
        sa.Column("geoweb_hub_slug", sa.String(200), nullable=True),
        sa.Column("meta", sa.JSON(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_geo_themes_slug"),
    )
    op.create_index("ix_geo_themes_status", "geo_themes", ["status"])
    op.create_index("ix_geo_themes_scene", "geo_themes", ["scene_id"])
    op.create_index("ix_geo_themes_task", "geo_themes", ["task_id"])

    op.add_column("articles", sa.Column("theme_id", sa.BigInteger(), nullable=True))
    op.create_index("ix_articles_theme", "articles", ["theme_id"])

    op.add_column(
        "geo_gap_remediation_runs",
        sa.Column("theme_id", sa.BigInteger(), nullable=True),
    )
    op.create_index("ix_gap_remediation_theme", "geo_gap_remediation_runs", ["theme_id"])


def downgrade() -> None:
    op.drop_index("ix_gap_remediation_theme", table_name="geo_gap_remediation_runs")
    op.drop_column("geo_gap_remediation_runs", "theme_id")
    op.drop_index("ix_articles_theme", table_name="articles")
    op.drop_column("articles", "theme_id")
    op.drop_index("ix_geo_themes_task", table_name="geo_themes")
    op.drop_index("ix_geo_themes_scene", table_name="geo_themes")
    op.drop_index("ix_geo_themes_status", table_name="geo_themes")
    op.drop_table("geo_themes")
