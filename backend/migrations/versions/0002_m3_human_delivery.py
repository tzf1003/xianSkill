"""M3 — 人工协助 SKU 业务闭环

变更：
- skus 表新增 human_sla_hours、human_price_cents
- 新增 webhooks 表（webhook 配置）
- 新增 delivery_records 表（人工交付审计记录）

Revision ID: 0002_m3_human_delivery
Revises: 0001_m1_core_tables
Create Date: 2026-03-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_m3_human_delivery"
down_revision: Union[str, None] = "0001_m1_core_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- skus: 增加人工协助字段 --
    op.add_column("skus", sa.Column("human_sla_hours", sa.Integer, nullable=True,
                                    comment="人工处理 SLA（小时）"))
    op.add_column("skus", sa.Column("human_price_cents", sa.Integer, nullable=True,
                                    comment="人工服务附加定价（分）"))

    # -- webhooks --
    op.create_table(
        "webhooks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("url", sa.String(2000), nullable=False),
        sa.Column("secret", sa.String(500), nullable=True, comment="HMAC-SHA256 签名密钥"),
        sa.Column("events", postgresql.JSONB, nullable=True, comment="订阅事件列表，null=全部"),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("enabled", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- delivery_records --
    op.create_table(
        "delivery_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("operator", sa.String(200), nullable=False, comment="操作人"),
        sa.Column("notes", sa.Text, nullable=True, comment="备注"),
        sa.Column("output_hash", sa.String(128), nullable=True, comment="产物 SHA-256"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_delivery_records_job_id", "delivery_records", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_delivery_records_job_id", table_name="delivery_records")
    op.drop_table("delivery_records")
    op.drop_table("webhooks")
    op.drop_column("skus", "human_price_cents")
    op.drop_column("skus", "human_sla_hours")
