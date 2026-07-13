"""竞品 entity_type 回填 — 按名称规则区分品牌与产品。"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "010_competitor_entity_backfill"
down_revision: Union[str, None] = "009_competitor_entity_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 与 entity_classifier.py 保持一致的 SQL 回填规则
_PRODUCT_SQL = """
UPDATE geo_monitor_competitors
SET entity_type = 'product'
WHERE entity_type = 'brand'
  AND (
    brand_name ~* '(ADS|FSD|XNGP|NOP\\+|DiPilot|IM AD|AvatarDrive|G-ASD|千里浩瀚|AD Max|AD Pro)'
    OR (brand_name ~ '[A-Za-z]' AND brand_name NOT LIKE '%汽车')
    OR brand_name LIKE '% %'
  )
"""


def upgrade() -> None:
    op.execute(_PRODUCT_SQL)


def downgrade() -> None:
    op.execute("UPDATE geo_monitor_competitors SET entity_type = 'brand'")
