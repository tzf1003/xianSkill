"""xgj reward modes and order mapping

Revision ID: 0015_xgj_reward_modes
Revises: 0014_skus_delivery_tpl
"""

from alembic import op
import sqlalchemy as sa


revision = "0015_xgj_reward_modes"
down_revision = "0014_skus_delivery_tpl"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE delivery_mode ADD VALUE IF NOT EXISTS 'after_receipt'")
    op.execute("ALTER TYPE delivery_mode ADD VALUE IF NOT EXISTS 'after_review'")
    op.add_column("xgj_orders", sa.Column("source_order_no", sa.String(length=100), nullable=True, comment="来源业务订单号/闲鱼订单号"))
    op.add_column("xgj_orders", sa.Column("local_order_id", sa.UUID(), nullable=True, comment="本地订单ID"))
    op.add_column("xgj_orders", sa.Column("local_token_id", sa.UUID(), nullable=True, comment="本地Token ID"))
    op.create_index("ix_xgj_orders_source_order_no", "xgj_orders", ["source_order_no"])
    op.create_index("ix_xgj_orders_local_order_id", "xgj_orders", ["local_order_id"])
    op.create_index("ix_xgj_orders_local_token_id", "xgj_orders", ["local_token_id"])


def downgrade() -> None:
    op.drop_index("ix_xgj_orders_local_token_id", table_name="xgj_orders")
    op.drop_index("ix_xgj_orders_local_order_id", table_name="xgj_orders")
    op.drop_index("ix_xgj_orders_source_order_no", table_name="xgj_orders")
    op.drop_column("xgj_orders", "local_token_id")
    op.drop_column("xgj_orders", "local_order_id")
    op.drop_column("xgj_orders", "source_order_no")