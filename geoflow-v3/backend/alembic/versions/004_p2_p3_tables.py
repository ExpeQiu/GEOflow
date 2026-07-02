"""P2/P3: content_agent_requests、geo_admin_alerts、url_import result_json。"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004_p2_p3"
down_revision: Union[str, None] = "003_monitor_webintel"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "content_agent_requests",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("workflow_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), server_default="pending", nullable=False),
        sa.Column("engine", sa.String(30), server_default=""),
        sa.Column("correlation_type", sa.String(50), server_default=""),
        sa.Column("correlation_id", sa.BigInteger(), nullable=True),
        sa.Column("error_message", sa.Text(), server_default=""),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
    )
    op.create_index("ix_car_workflow_status", "content_agent_requests", ["workflow_type", "status"])

    op.create_table(
        "geo_admin_alerts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_geo_admin_alerts_type", "geo_admin_alerts", ["alert_type"])

    op.add_column("url_import_jobs", sa.Column("result_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("url_import_jobs", "result_json")
    op.drop_table("geo_admin_alerts")
    op.drop_index("ix_car_workflow_status", table_name="content_agent_requests")
    op.drop_table("content_agent_requests")
