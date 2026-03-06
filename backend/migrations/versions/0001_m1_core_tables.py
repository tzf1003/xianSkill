"""M1 — 核心表 skills/skus/orders/tokens/jobs/assets

Revision ID: 0001_m1_core_tables
Revises:
Create Date: 2026-03-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_m1_core_tables"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- Enum types --
    skill_type = postgresql.ENUM("prompt", "external_service", "workflow", "client_exec", name="skill_type", create_type=False)
    delivery_mode = postgresql.ENUM("auto", "human", name="delivery_mode", create_type=False)
    order_status = postgresql.ENUM("pending", "paid", "canceled", name="order_status", create_type=False)
    token_status = postgresql.ENUM("active", "expired", "revoked", name="token_status", create_type=False)
    job_status = postgresql.ENUM("queued", "running", "succeeded", "failed", "canceled", name="job_status", create_type=False)

    for e in [skill_type, delivery_mode, order_status, token_status, job_status]:
        e.create(op.get_bind(), checkfirst=True)

    # -- skills --
    op.create_table(
        "skills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("type", skill_type, nullable=False),
        sa.Column("version", sa.String(50), server_default="1.0.0"),
        sa.Column("input_schema", postgresql.JSONB, nullable=True),
        sa.Column("output_schema", postgresql.JSONB, nullable=True),
        sa.Column("enabled", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- skus --
    op.create_table(
        "skus",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("skill_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("price_cents", sa.Integer, server_default="0"),
        sa.Column("delivery_mode", delivery_mode, server_default="auto"),
        sa.Column("total_uses", sa.Integer, server_default="1"),
        sa.Column("enabled", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_skus_skill_id", "skus", ["skill_id"])

    # -- orders --
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sku_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("skus.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", order_status, server_default="paid"),
        sa.Column("channel", sa.String(100), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_orders_sku_id", "orders", ["sku_id"])

    # -- tokens --
    op.create_table(
        "tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("token", sa.String(64), unique=True, nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("sku_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("skill_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", token_status, server_default="active"),
        sa.Column("total_uses", sa.Integer, nullable=False),
        sa.Column("used_count", sa.Integer, server_default="0"),
        sa.Column("reserved_count", sa.Integer, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tokens_token", "tokens", ["token"])
    op.create_index("ix_tokens_sku_id", "tokens", ["sku_id"])
    op.create_index("ix_tokens_skill_id", "tokens", ["skill_id"])

    # -- jobs --
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("token_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tokens.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", job_status, server_default="queued"),
        sa.Column("idempotency_key", sa.String(128), nullable=True),
        sa.Column("inputs", postgresql.JSONB, nullable=True),
        sa.Column("result", postgresql.JSONB, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_jobs_token_id", "jobs", ["token_id"])
    op.create_index("ix_jobs_idempotency", "jobs", ["token_id", "idempotency_key"], unique=True)

    # -- assets --
    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("content_type", sa.String(200), nullable=True),
        sa.Column("size_bytes", sa.Integer, nullable=True),
        sa.Column("hash", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_assets_job_id", "assets", ["job_id"])


def downgrade() -> None:
    op.drop_table("assets")
    op.drop_table("jobs")
    op.drop_table("tokens")
    op.drop_table("orders")
    op.drop_table("skus")
    op.drop_table("skills")
    for name in ["job_status", "token_status", "order_status", "delivery_mode", "skill_type"]:
        sa.Enum(name=name).drop(op.get_bind(), checkfirst=True)
