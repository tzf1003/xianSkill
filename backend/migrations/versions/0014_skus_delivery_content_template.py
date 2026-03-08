"""skus: add delivery_content_template

Revision ID: 0014_skus_delivery_tpl
Revises: 0013_goods_specs_xgj_sku
"""

from alembic import op
import sqlalchemy as sa


revision = "0014_skus_delivery_tpl"
down_revision = "0013_goods_specs_xgj_sku"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("skus", sa.Column("delivery_content_template", sa.Text(), nullable=True, comment="卡密/券码发货内容模板"))


def downgrade() -> None:
    op.drop_column("skus", "delivery_content_template")