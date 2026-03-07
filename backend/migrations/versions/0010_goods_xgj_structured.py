"""goods: structured xgj profile tables

Revision ID: 0010_goods_xgj_struct
Revises: 0009_goods_spec_groups
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_goods_xgj_struct"
down_revision = "0009_goods_spec_groups"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("goods_specs", sa.Column("xgj_sku_text", sa.String(length=200), nullable=True, comment="闲管家SKU规格文本"))
    op.add_column("goods_specs", sa.Column("xgj_outer_id", sa.String(length=100), nullable=True, comment="闲管家SKU外部编码"))

    op.create_table(
        "goods_xgj_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("goods_id", sa.Uuid(), nullable=False),
        sa.Column("item_biz_type", sa.Integer(), nullable=False),
        sa.Column("sp_biz_type", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("channel_cat_id", sa.String(length=100), nullable=False),
        sa.Column("original_price_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("express_fee_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stuff_status", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notify_url", sa.String(length=2000), nullable=True),
        sa.Column("flash_sale_type", sa.Integer(), nullable=True),
        sa.Column("is_tax_included", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("product_status", sa.Integer(), nullable=True),
        sa.Column("publish_status", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["goods_id"], ["goods.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("goods_id"),
    )
    op.create_index("ix_goods_xgj_profiles_goods_id", "goods_xgj_profiles", ["goods_id"])

    op.create_table(
        "goods_xgj_properties",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("goods_id", sa.Uuid(), nullable=False),
        sa.Column("property_id", sa.String(length=100), nullable=False),
        sa.Column("property_name", sa.String(length=100), nullable=False),
        sa.Column("value_id", sa.String(length=100), nullable=False),
        sa.Column("value_name", sa.String(length=100), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["goods_id"], ["goods.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_goods_xgj_properties_goods_id", "goods_xgj_properties", ["goods_id"])
    op.create_index("ix_goods_xgj_properties_sort_order", "goods_xgj_properties", ["goods_id", "sort_order"])

    op.create_table(
        "goods_xgj_publish_shops",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("goods_id", sa.Uuid(), nullable=False),
        sa.Column("user_name", sa.String(length=100), nullable=False),
        sa.Column("province", sa.Integer(), nullable=False),
        sa.Column("city", sa.Integer(), nullable=False),
        sa.Column("district", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=60), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("white_image_url", sa.String(length=500), nullable=True),
        sa.Column("service_support", sa.String(length=200), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["goods_id"], ["goods.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_goods_xgj_publish_shops_goods_id", "goods_xgj_publish_shops", ["goods_id"])
    op.create_index("ix_goods_xgj_publish_shops_sort_order", "goods_xgj_publish_shops", ["goods_id", "sort_order"])

    op.create_table(
        "goods_xgj_publish_shop_images",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shop_id", sa.Uuid(), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["shop_id"], ["goods_xgj_publish_shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_goods_xgj_publish_shop_images_shop_id", "goods_xgj_publish_shop_images", ["shop_id"])
    op.create_index("ix_goods_xgj_publish_shop_images_sort_order", "goods_xgj_publish_shop_images", ["shop_id", "sort_order"])


def downgrade() -> None:
    op.drop_index("ix_goods_xgj_publish_shop_images_sort_order", table_name="goods_xgj_publish_shop_images")
    op.drop_index("ix_goods_xgj_publish_shop_images_shop_id", table_name="goods_xgj_publish_shop_images")
    op.drop_table("goods_xgj_publish_shop_images")

    op.drop_index("ix_goods_xgj_publish_shops_sort_order", table_name="goods_xgj_publish_shops")
    op.drop_index("ix_goods_xgj_publish_shops_goods_id", table_name="goods_xgj_publish_shops")
    op.drop_table("goods_xgj_publish_shops")

    op.drop_index("ix_goods_xgj_properties_sort_order", table_name="goods_xgj_properties")
    op.drop_index("ix_goods_xgj_properties_goods_id", table_name="goods_xgj_properties")
    op.drop_table("goods_xgj_properties")

    op.drop_index("ix_goods_xgj_profiles_goods_id", table_name="goods_xgj_profiles")
    op.drop_table("goods_xgj_profiles")

    op.drop_column("goods_specs", "xgj_outer_id")
    op.drop_column("goods_specs", "xgj_sku_text")