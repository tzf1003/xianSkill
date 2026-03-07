"""goods: add logo_url, multi_spec, xgj_goods_id columns

Revision ID: 0008
Revises: 0007
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_goods_logo_multi_xgj"
down_revision = "0007_goods_virtual_source"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("goods", sa.Column("logo_url", sa.String(500), nullable=True, comment="商品图片/Logo URL"))
    op.add_column("goods", sa.Column("multi_spec", sa.Boolean(), server_default=sa.text("false"), nullable=False, comment="是否多规格商品"))
    op.add_column("goods", sa.Column("xgj_goods_id", sa.String(100), nullable=True, comment="闲管家商品ID(绑定后由闲管家分配)"))
    op.create_index("ix_goods_xgj_goods_id", "goods", ["xgj_goods_id"])


def downgrade() -> None:
    op.drop_index("ix_goods_xgj_goods_id", table_name="goods")
    op.drop_column("goods", "xgj_goods_id")
    op.drop_column("goods", "multi_spec")
    op.drop_column("goods", "logo_url")
