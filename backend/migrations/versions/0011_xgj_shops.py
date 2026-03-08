"""add xgj shops table

Revision ID: 0011_xgj_shops
Revises: 0010_goods_xgj_struct
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_xgj_shops"
down_revision = "0010_goods_xgj_struct"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "xgj_shops",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("authorize_id", sa.BigInteger(), nullable=False),
        sa.Column("authorize_expires", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("user_identity", sa.String(length=255), nullable=False),
        sa.Column("user_name", sa.String(length=255), nullable=False),
        sa.Column("user_nick", sa.String(length=255), nullable=False),
        sa.Column("shop_name", sa.String(length=255), nullable=False),
        sa.Column("service_support", sa.String(length=255), nullable=True),
        sa.Column("is_deposit_enough", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_pro", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_valid", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_trial", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("valid_start_time", sa.Integer(), nullable=True),
        sa.Column("valid_end_time", sa.Integer(), nullable=False),
        sa.Column("item_biz_types", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("authorize_id"),
    )
    op.create_index("ix_xgj_shops_authorize_id", "xgj_shops", ["authorize_id"])
    op.create_index("ix_xgj_shops_is_valid", "xgj_shops", ["is_valid"])
    op.create_index("ix_xgj_shops_user_name", "xgj_shops", ["user_name"])


def downgrade() -> None:
    op.drop_index("ix_xgj_shops_user_name", table_name="xgj_shops")
    op.drop_index("ix_xgj_shops_is_valid", table_name="xgj_shops")
    op.drop_index("ix_xgj_shops_authorize_id", table_name="xgj_shops")
    op.drop_table("xgj_shops")