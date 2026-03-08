"""goods_specs: add xgj_sku_id

Revision ID: 0013_goods_specs_xgj_sku
Revises: 0012_goods_shop_ref
"""

from alembic import op
import sqlalchemy as sa


revision = "0013_goods_specs_xgj_sku"
down_revision = "0012_goods_shop_ref"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("goods_specs", sa.Column("xgj_sku_id", sa.String(length=100), nullable=True, comment="闲管家云端SKU ID"))
    op.create_index("ix_goods_specs_xgj_sku_id", "goods_specs", ["goods_id", "xgj_sku_id"])


def downgrade() -> None:
    op.drop_index("ix_goods_specs_xgj_sku_id", table_name="goods_specs")
    op.drop_column("goods_specs", "xgj_sku_id")