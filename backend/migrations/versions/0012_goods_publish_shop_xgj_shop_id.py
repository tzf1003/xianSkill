"""link goods publish shops to xgj shops

Revision ID: 0012_goods_shop_ref
Revises: 0011_xgj_shops
"""

from alembic import op
import sqlalchemy as sa


revision = "0012_goods_shop_ref"
down_revision = "0011_xgj_shops"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("goods_xgj_publish_shops", sa.Column("xgj_shop_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_goods_xgj_publish_shops_xgj_shop_id",
        "goods_xgj_publish_shops",
        "xgj_shops",
        ["xgj_shop_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_goods_xgj_publish_shops_xgj_shop_id", "goods_xgj_publish_shops", ["xgj_shop_id"])


def downgrade() -> None:
    op.drop_index("ix_goods_xgj_publish_shops_xgj_shop_id", table_name="goods_xgj_publish_shops")
    op.drop_constraint("fk_goods_xgj_publish_shops_xgj_shop_id", "goods_xgj_publish_shops", type_="foreignkey")
    op.drop_column("goods_xgj_publish_shops", "xgj_shop_id")