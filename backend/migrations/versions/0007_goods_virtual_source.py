"""0007 — 虚拟货源商品管理：goods / goods_specs / spec_sku_bindings / goods_subscriptions / xgj_orders

Revision ID: 0007_goods_virtual_source
Revises: 0006_jobs_log_hash_cols
Create Date: 2026-03-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007_goods_virtual_source"
down_revision: Union[str, None] = "0006_jobs_log_hash_cols"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── goods ──
    op.create_table(
        "goods",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("goods_no", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("goods_type", sa.Integer, nullable=False, comment="1=直充 2=卡密 3=券码"),
        sa.Column("goods_name", sa.String(500), nullable=False),
        sa.Column("price_cents", sa.Integer, server_default="0", comment="成本价(分)"),
        sa.Column("stock", sa.Integer, server_default="0"),
        sa.Column("status", sa.Integer, server_default="1", comment="1=在架 2=下架"),
        sa.Column("template", sa.JSON, nullable=True, comment="充值模板(直充商品)"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── goods_specs ──
    op.create_table(
        "goods_specs",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("goods_id", sa.Uuid, sa.ForeignKey("goods.id", ondelete="CASCADE"), nullable=False),
        sa.Column("spec_name", sa.String(200), nullable=False),
        sa.Column("price_cents", sa.Integer, server_default="0"),
        sa.Column("stock", sa.Integer, server_default="0"),
        sa.Column("enabled", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_goods_specs_goods_id", "goods_specs", ["goods_id"])

    # ── spec_sku_bindings ──
    op.create_table(
        "spec_sku_bindings",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("spec_id", sa.Uuid, sa.ForeignKey("goods_specs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("timing", sa.String(50), nullable=False, comment="发货时机"),
        sa.Column("sku_id", sa.Uuid, sa.ForeignKey("skus.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_spec_sku_bindings_spec_id", "spec_sku_bindings", ["spec_id"])
    op.create_index("uq_spec_timing", "spec_sku_bindings", ["spec_id", "timing"], unique=True)

    # ── goods_subscriptions ──
    op.create_table(
        "goods_subscriptions",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("goods_id", sa.Uuid, sa.ForeignKey("goods.id", ondelete="CASCADE"), nullable=False),
        sa.Column("notify_url", sa.String(2000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_goods_subscriptions_goods_id", "goods_subscriptions", ["goods_id"])

    # ── xgj_orders ──
    op.create_table(
        "xgj_orders",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("order_no", sa.String(100), unique=True, nullable=False, index=True, comment="闲管家订单号"),
        sa.Column("out_order_no", sa.String(100), unique=True, nullable=False, index=True, comment="我方订单号"),
        sa.Column("goods_no", sa.String(100), nullable=False),
        sa.Column("spec_id", sa.Uuid, nullable=True),
        sa.Column("goods_type", sa.Integer, nullable=False),
        sa.Column("status", sa.Integer, server_default="0", comment="订单状态"),
        sa.Column("quantity", sa.Integer, server_default="1"),
        sa.Column("total_price_cents", sa.Integer, server_default="0"),
        sa.Column("buyer_info", sa.JSON, nullable=True),
        sa.Column("delivery_info", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("xgj_orders")
    op.drop_table("goods_subscriptions")
    op.drop_table("spec_sku_bindings")
    op.drop_table("goods_specs")
    op.drop_table("goods")
