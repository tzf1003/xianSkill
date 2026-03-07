"""goods: add spec_groups JSON column

Revision ID: 0009_goods_spec_groups
Revises: 0008_goods_logo_multi_xgj
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_goods_spec_groups"
down_revision = "0008_goods_logo_multi_xgj"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("goods", sa.Column("spec_groups", sa.JSON(), nullable=True, comment="规格维度定义 [{name,values}], 最多2组"))


def downgrade() -> None:
    op.drop_column("goods", "spec_groups")
