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


class GoodsType(int, enum.Enum):
    """虚拟货源商品类型"""
    recharge = 1   # 直充
    card_key = 2   # 卡密
    coupon = 3     # 券码


class GoodsStatus(int, enum.Enum):
    """虚拟货源商品状态"""
    on_shelf = 1   # 在架
    off_shelf = 2  # 下架


class DeliveryTiming(str, enum.Enum):
    """发货时机"""
    after_payment = "after_payment"  # 付款后发货
    after_receipt = "after_receipt"  # 收货后赠送
    after_review = "after_review"   # 好评后赠送


class XgjOrderStatus(int, enum.Enum):
    """闲管家虚拟货源订单状态"""
    pending = 0       # 待处理
    processing = 1    # 处理中
    success = 2       # 成功
    failed = 3        # 失败
    refunding = 4     # 退款中
    refunded = 5      # 已退款


# ── Mixin ─────────────────────────────────────────────────────────────
class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


# ── Project ───────────────────────────────────────────────────────────
class Project(Base, TimestampMixin):
    """options 字段示例：

        {
          "option_groups": [
            {
              "id": "colorize",
              "label": "添加彩色效果",
              "description": "将黑白老照片智能上色",
              "type": "toggle",          # "toggle" | "single_choice"
              "default": false,
              "icon": "🎨",
              "prompt_addition": "对照片进行智能上色，让黑白照片重现彩色生机"
            },
            {
              "id": "repair_mode",
              "label": "修复方案",
              "type": "single_choice",
              "default": "default",
              "choices": [
                {"id": "default", "label": "默认版", "icon": "✨", "prompt_addition": ""},
                {"id": "heavy",   "label": "重度破损修复", "icon": "🔧", "prompt_addition": "..."}
              ]
            }
          ]
        }
    """

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False, default="photo_restore")
    options: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="定制化选项组配置 JSON")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    skill_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("skills.id", ondelete="SET NULL"), nullable=True,
        comment="该项目绑定的默认 Skill"
    )

    skus: Mapped[list["SKU"]] = relationship("SKU", back_populates="project", lazy="selectin")
    skill: Mapped["Skill | None"] = relationship("Skill", foreign_keys=[skill_id], lazy="selectin")


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
    prompt_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    runner_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    skus: Mapped[list["SKU"]] = relationship("SKU", back_populates="skill", lazy="selectin")


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
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True,
        comment="该 SKU 属于哪个项目（决定运行时加载哪个 Project 的选项配置）"
    )
    # ── 人工协助扩展字段 ─────────────────────────────────────────────
    human_sla_hours: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="人工处理 SLA（小时）")
    human_price_cents: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="人工服务附加定价（分）")

    skill: Mapped[Skill] = relationship("Skill", back_populates="skus")
    project: Mapped["Project | None"] = relationship("Project", back_populates="skus", lazy="selectin")
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
    log_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    output_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    token: Mapped[Token] = relationship("Token", back_populates="jobs")
    assets: Mapped[list[Asset]] = relationship("Asset", back_populates="job", lazy="selectin")
    delivery_record: Mapped[DeliveryRecord | None] = relationship(
        "DeliveryRecord", back_populates="job", uselist=False, lazy="selectin"
    )

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


# ── Webhook ───────────────────────────────────────────────────────────
class Webhook(Base, TimestampMixin):
    """Webhook 配置 — 订单付款等事件时向外部 URL 推送通知。"""

    __tablename__ = "webhooks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    secret: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="HMAC-SHA256 签名密钥")
    events: Mapped[list | None] = mapped_column(JSON, nullable=True, comment="订阅事件列表，null = 全部")
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


# ── DeliveryRecord ────────────────────────────────────────────────────
class DeliveryRecord(Base, TimestampMixin):
    """人工交付记录 — 操作审计证据（AGENT.md §6）。"""

    __tablename__ = "delivery_records"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    operator: Mapped[str] = mapped_column(String(200), nullable=False, comment="操作人")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    output_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="产物 SHA-256")

    job: Mapped[Job] = relationship("Job", back_populates="delivery_record")

    __table_args__ = (Index("ix_delivery_records_job_id", "job_id"),)


# ── Goods（虚拟货源商品）──────────────────────────────────────────────
class Goods(Base, TimestampMixin):
    """虚拟货源商品 — 对应闲管家虚拟货源标准接口中的商品。"""

    __tablename__ = "goods"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    goods_no: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True, comment="商品编号(系统自动生成)")
    goods_type: Mapped[int] = mapped_column(Integer, nullable=False, comment="商品类型 1=直充 2=卡密 3=券码")
    goods_name: Mapped[str] = mapped_column(String(500), nullable=False, comment="商品名称")
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="商品图片/Logo URL")
    price_cents: Mapped[int] = mapped_column(Integer, default=0, comment="成本价(分)")
    stock: Mapped[int] = mapped_column(Integer, default=0, comment="库存数量")
    status: Mapped[int] = mapped_column(Integer, default=1, comment="状态 1=在架 2=下架")
    multi_spec: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否多规格商品")
    xgj_goods_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True, comment="闲管家商品ID(绑定后由闲管家分配)")
    spec_groups: Mapped[list | None] = mapped_column(JSON, nullable=True, comment="规格维度定义 [{name,values}], 最多2组")
    template: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="充值模板(直充商品)")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    specs: Mapped[list["GoodsSpec"]] = relationship("GoodsSpec", back_populates="goods", lazy="selectin", cascade="all, delete-orphan")
    subscriptions: Mapped[list["GoodsSubscription"]] = relationship("GoodsSubscription", back_populates="goods", lazy="selectin", cascade="all, delete-orphan")


# ── GoodsSpec（商品规格）──────────────────────────────────────────────
class GoodsSpec(Base, TimestampMixin):
    """商品规格 — 每个商品可有多个规格。"""

    __tablename__ = "goods_specs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    goods_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("goods.id", ondelete="CASCADE"), nullable=False
    )
    spec_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="规格名称")
    price_cents: Mapped[int] = mapped_column(Integer, default=0, comment="规格价格(分)")
    stock: Mapped[int] = mapped_column(Integer, default=0, comment="规格库存")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    goods: Mapped[Goods] = relationship("Goods", back_populates="specs")
    sku_bindings: Mapped[list["SpecSkuBinding"]] = relationship(
        "SpecSkuBinding", back_populates="spec", lazy="selectin", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_goods_specs_goods_id", "goods_id"),)


# ── SpecSkuBinding（规格-SKU 发货时机绑定）───────────────────────────
class SpecSkuBinding(Base, TimestampMixin):
    """规格与 SKU 的发货时机绑定。

    每个规格可分别在 3 个发货时机绑定不同的 SKU：
    - after_payment: 付款后发货
    - after_receipt: 收货后赠送
    - after_review:  好评后赠送
    """

    __tablename__ = "spec_sku_bindings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    spec_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("goods_specs.id", ondelete="CASCADE"), nullable=False
    )
    timing: Mapped[DeliveryTiming] = mapped_column(
        Enum(DeliveryTiming, name="delivery_timing", native_enum=False), nullable=False,
        comment="发货时机"
    )
    sku_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("skus.id", ondelete="SET NULL"), nullable=True,
        comment="绑定的 SKU"
    )

    spec: Mapped[GoodsSpec] = relationship("GoodsSpec", back_populates="sku_bindings")
    sku: Mapped["SKU | None"] = relationship("SKU", foreign_keys=[sku_id], lazy="selectin")

    __table_args__ = (
        Index("ix_spec_sku_bindings_spec_id", "spec_id"),
        Index("uq_spec_timing", "spec_id", "timing", unique=True),
    )


# ── GoodsSubscription（商品变更订阅）─────────────────────────────────
class GoodsSubscription(Base, TimestampMixin):
    """闲管家对我方商品的变更通知订阅关系。"""

    __tablename__ = "goods_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    goods_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("goods.id", ondelete="CASCADE"), nullable=False
    )
    notify_url: Mapped[str] = mapped_column(String(2000), nullable=False, comment="闲管家通知回调URL")

    goods: Mapped[Goods] = relationship("Goods", back_populates="subscriptions")

    __table_args__ = (
        Index("ix_goods_subscriptions_goods_id", "goods_id"),
    )


# ── XgjOrder（闲管家虚拟货源订单）────────────────────────────────────
class XgjOrder(Base, TimestampMixin):
    """闲管家虚拟货源下单记录。"""

    __tablename__ = "xgj_orders"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    order_no: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True, comment="闲管家订单号")
    out_order_no: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True, comment="我方订单号")
    goods_no: Mapped[str] = mapped_column(String(100), nullable=False, comment="商品编号")
    spec_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, comment="规格ID")
    goods_type: Mapped[int] = mapped_column(Integer, nullable=False, comment="商品类型")
    status: Mapped[int] = mapped_column(Integer, default=0, comment="订单状态")
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    total_price_cents: Mapped[int] = mapped_column(Integer, default=0, comment="总价(分)")
    buyer_info: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="买家信息/充值账号等")
    delivery_info: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="发货信息(卡密/券码等)")
