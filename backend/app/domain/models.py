"""SQLAlchemy ORM 模型 — 最小必需表。

按 AGENT.md §3 Domain Model + §6 Token 安全与计次规则设计。
Job 状态机：queued → running → succeeded | failed | canceled
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ── Base ──────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """所有模型的声明式基类。"""


# ── Enums ─────────────────────────────────────────────────────────────
class SkillType(str, enum.Enum):
    prompt = "prompt"
    external_service = "external_service"
    workflow = "workflow"
    client_exec = "client_exec"


class DeliveryMode(str, enum.Enum):
    auto = "auto"
    human = "human"


class OrderStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    canceled = "canceled"


class TokenStatus(str, enum.Enum):
    active = "active"
    expired = "expired"
    revoked = "revoked"


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    canceled = "canceled"


# ── Mixin ─────────────────────────────────────────────────────────────
class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


# ── Skill ─────────────────────────────────────────────────────────────
class Skill(Base, TimestampMixin):
    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[SkillType] = mapped_column(Enum(SkillType, name="skill_type", native_enum=False), nullable=False)
    version: Mapped[str] = mapped_column(String(50), default="1.0.0")
    input_schema: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output_schema: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    skus: Mapped[list[SKU]] = relationship("SKU", back_populates="skill", lazy="selectin")


# ── SKU ───────────────────────────────────────────────────────────────
class SKU(Base, TimestampMixin):
    __tablename__ = "skus"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    skill_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, default=0)
    delivery_mode: Mapped[DeliveryMode] = mapped_column(
        Enum(DeliveryMode, name="delivery_mode", native_enum=False), default=DeliveryMode.auto
    )
    total_uses: Mapped[int] = mapped_column(Integer, default=1, comment="该 SKU 允许使用的总次数")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    skill: Mapped[Skill] = relationship("Skill", back_populates="skus")
    orders: Mapped[list[Order]] = relationship("Order", back_populates="sku", lazy="selectin")

    __table_args__ = (Index("ix_skus_skill_id", "skill_id"),)


# ── Order ─────────────────────────────────────────────────────────────
class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    sku_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("skus.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status", native_enum=False), default=OrderStatus.paid
    )
    channel: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="来源渠道")
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    sku: Mapped[SKU] = relationship("SKU", back_populates="orders")
    token: Mapped[Token | None] = relationship("Token", back_populates="order", uselist=False)

    __table_args__ = (Index("ix_orders_sku_id", "sku_id"),)


# ── Token ─────────────────────────────────────────────────────────────
class Token(Base, TimestampMixin):
    """交付凭证。

    安全要求（AGENT.md §6）：
    - token >= 128-bit 随机，URL-safe
    - scope 限制：绑定 sku_id / skill_id
    - 两阶段计次：reserve / finalize
    """

    __tablename__ = "tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    sku_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    skill_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    status: Mapped[TokenStatus] = mapped_column(
        Enum(TokenStatus, name="token_status", native_enum=False), default=TokenStatus.active
    )
    total_uses: Mapped[int] = mapped_column(Integer, nullable=False, comment="允许总次数")
    used_count: Mapped[int] = mapped_column(Integer, default=0, comment="已确认消耗次数")
    reserved_count: Mapped[int] = mapped_column(Integer, default=0, comment="已冻结（待确认）次数")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    order: Mapped[Order] = relationship("Order", back_populates="token")
    jobs: Mapped[list[Job]] = relationship("Job", back_populates="token", lazy="selectin")

    __table_args__ = (
        Index("ix_tokens_sku_id", "sku_id"),
        Index("ix_tokens_skill_id", "skill_id"),
    )

    @property
    def remaining(self) -> int:
        """可用剩余次数 = 总次数 - 已用 - 已冻结。"""
        return self.total_uses - self.used_count - self.reserved_count


# ── Job ───────────────────────────────────────────────────────────────
class Job(Base, TimestampMixin):
    """一次执行。状态机：queued → running → succeeded | failed | canceled"""

    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    token_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tokens.id", ondelete="CASCADE"), nullable=False
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status", native_enum=False), default=JobStatus.queued
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    inputs: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    token: Mapped[Token] = relationship("Token", back_populates="jobs")
    assets: Mapped[list[Asset]] = relationship("Asset", back_populates="job", lazy="selectin")

    __table_args__ = (
        Index("ix_jobs_token_id", "token_id"),
        Index("ix_jobs_idempotency", "token_id", "idempotency_key", unique=True),
    )


# ── Asset ─────────────────────────────────────────────────────────────
class Asset(Base, TimestampMixin):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(200), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hash: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="SHA-256")

    job: Mapped[Job] = relationship("Job", back_populates="assets")

    __table_args__ = (Index("ix_assets_job_id", "job_id"),)
