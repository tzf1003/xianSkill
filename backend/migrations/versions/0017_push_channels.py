"""add push channels and human sku binding

Revision ID: 0017_push_channels
Revises: 0016_ai_providers
"""

from alembic import op
import sqlalchemy as sa


revision = "0017_push_channels"
down_revision = "0016_ai_providers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "push_channels",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False, server_default="bark"),
        sa.Column("base_url", sa.String(length=1000), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.add_column("skus", sa.Column("push_channel_id", sa.UUID(), nullable=True, comment="人工处理消息推送途径"))
    op.create_index("ix_skus_push_channel_id", "skus", ["push_channel_id"])
    op.create_foreign_key(
        "fk_skus_push_channel_id",
        "skus",
        "push_channels",
        ["push_channel_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_skus_push_channel_id", "skus", type_="foreignkey")
    op.drop_index("ix_skus_push_channel_id", table_name="skus")
    op.drop_column("skus", "push_channel_id")
    op.drop_table("push_channels")