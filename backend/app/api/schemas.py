"""Pydantic schemas for API 请求/响应。"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── 通用响应包装 ──────────────────────────────────────────────────────
class ApiResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: dict | list | None = None


# ── Project ──────────────────────────────────────────────────────────
class ProjectCreate(BaseModel):
    name: str = Field(..., max_length=200)
    slug: str = Field(..., max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str | None = None
    cover_url: str | None = None
    type: str = "photo_restore"
    options: dict | None = None  # 选项组 JSON（见 Project 模型注释）
    skill_id: uuid.UUID | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    cover_url: str | None = None
    type: str | None = None
    options: dict | None = None
    enabled: bool | None = None
    skill_id: uuid.UUID | None = None


class ProjectOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    cover_url: str | None
    type: str
    options: dict | None
    enabled: bool
    skill_id: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Skill ─────────────────────────────────────────────────────────────
class SkillCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: str | None = None
    type: str = Field(..., pattern=r"^(prompt|external_service|workflow|client_exec)$")
    version: str = "1.0.0"
    input_schema: dict | None = None
    output_schema: dict | None = None
    prompt_template: str | None = None
    runner_config: dict | None = None


class SkillOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    type: str
    version: str
    enabled: bool
    prompt_template: str | None = None
    runner_config: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── SKU ───────────────────────────────────────────────────────────────
class SKUCreate(BaseModel):
    skill_id: uuid.UUID
    name: str = Field(..., max_length=200)
    price_cents: int = 0
    delivery_mode: str = Field("auto", pattern=r"^(auto|human)$")
    total_uses: int = Field(1, ge=1)
    human_sla_hours: int | None = None
    human_price_cents: int | None = None
    project_id: uuid.UUID | None = None


class SKUOut(BaseModel):
    id: uuid.UUID
    skill_id: uuid.UUID
    name: str
    price_cents: int
    delivery_mode: str
    total_uses: int
    enabled: bool
    human_sla_hours: int | None = None
    human_price_cents: int | None = None
    project_id: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Order ─────────────────────────────────────────────────────────────
class OrderCreate(BaseModel):
    sku_id: uuid.UUID
    channel: str | None = None


class OrderOut(BaseModel):
    id: uuid.UUID
    sku_id: uuid.UUID
    status: str
    channel: str | None
    token_url: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Token ─────────────────────────────────────────────────────────────
class LatestJobBrief(BaseModel):
    """Token 关联的最新 Job 简要，为前端显示状态提供最小信息。"""
    id: uuid.UUID
    status: str
    created_at: datetime
    finished_at: datetime | None = None
    assets: list["AssetOut"] = []

    model_config = {"from_attributes": True}


class TokenInfo(BaseModel):
    token: str
    skill: SkillOut
    sku_name: str
    delivery_mode: str = "auto"
    human_sla_hours: int | None = None
    total_uses: int
    remaining: int
    status: str
    expires_at: datetime | None
    latest_job: LatestJobBrief | None = None
    project: "ProjectOut | None" = None  # 如果技能绑定了项目则返回项目定制化选项

    model_config = {"from_attributes": True}


# ── Job ───────────────────────────────────────────────────────────────
class JobSubmit(BaseModel):
    token: str
    idempotency_key: str | None = None
    inputs: dict | None = None


class JobOut(BaseModel):
    id: uuid.UUID
    skill_id: uuid.UUID
    status: str
    inputs: dict | None
    result: dict | None
    error: str | None
    log_text: str | None = None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    assets: list["AssetOut"] = []

    model_config = {"from_attributes": True}


# ── Asset ─────────────────────────────────────────────────────────────
class AssetOut(BaseModel):
    id: uuid.UUID
    filename: str
    storage_key: str
    content_type: str | None
    size_bytes: int | None
    download_url: str = ""

    model_config = {"from_attributes": True}


# ── Upload ────────────────────────────────────────────────────────────
class UploadOut(BaseModel):
    object_key: str
    input_hash: str


# ── Admin: Update schemas ─────────────────────────────────────────────
class SkillUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    version: str | None = None
    input_schema: dict | None = None
    output_schema: dict | None = None
    prompt_template: str | None = None
    runner_config: dict | None = None
    enabled: bool | None = None


class SKUUpdate(BaseModel):
    name: str | None = None
    price_cents: int | None = None
    delivery_mode: str | None = None
    total_uses: int | None = None
    enabled: bool | None = None
    human_sla_hours: int | None = None
    human_price_cents: int | None = None
    project_id: uuid.UUID | None = None


# ── Admin: Token ─────────────────────────────────────────────────
class TokenCreate(BaseModel):
    """管理员手动创建 Token（自动建立 Manual 订单）。"""
    sku_id: uuid.UUID
    total_uses: int | None = None    # None 表示使用 SKU 默认值
    expires_at: datetime | None = None
    channel: str | None = "manual"


class TokenOut(BaseModel):
    id: uuid.UUID
    token: str
    order_id: uuid.UUID
    sku_id: uuid.UUID
    skill_id: uuid.UUID
    status: str
    total_uses: int
    used_count: int
    reserved_count: int
    remaining: int
    expires_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}

# ── Webhook ──────────────────────────────────────────────────────────────
class WebhookCreate(BaseModel):
    url: str = Field(..., max_length=2000)
    secret: str | None = Field(None, max_length=500)
    events: list[str] | None = None  # None = 订阅全部事件
    description: str | None = Field(None, max_length=500)


class WebhookOut(BaseModel):
    id: uuid.UUID
    url: str
    events: list[str] | None
    description: str | None
    enabled: bool
    created_at: datetime
    # 注意：secret 不回显

    model_config = {"from_attributes": True}


# ── DeliveryRecord ─────────────────────────────────────────────────────
class DeliveryRecordOut(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    operator: str
    notes: str | None
    output_hash: str | None
    created_at: datetime

    model_config = {"from_attributes": True}

# ── Admin: Stats ──────────────────────────────────────────────────────
class StatsOut(BaseModel):
    total_skills: int
    total_skus: int
    total_orders: int
    total_tokens: int
    total_jobs: int
    jobs_queued: int
    jobs_running: int
    jobs_succeeded: int
    jobs_failed: int


# ── Goods（虚拟货源商品）─────────────────────────────────────────────
class SpecSkuBindingIn(BaseModel):
    """规格-SKU 发货时机绑定（写入用）"""
    timing: str = Field(..., pattern=r"^(after_payment|after_receipt|after_review)$")
    sku_id: uuid.UUID | None = None


class SpecSkuBindingOut(BaseModel):
    id: uuid.UUID
    timing: str
    sku_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class GoodsSpecCreate(BaseModel):
    spec_name: str = Field(..., max_length=200)
    price_cents: int = 0
    stock: int = 0
    enabled: bool = True
    xgj_sku_text: str | None = None
    xgj_outer_id: str | None = None
    sku_bindings: list[SpecSkuBindingIn] = []


class GoodsSpecUpdate(BaseModel):
    spec_name: str | None = None
    price_cents: int | None = None
    stock: int | None = None
    enabled: bool | None = None
    xgj_sku_text: str | None = None
    xgj_outer_id: str | None = None


class GoodsSpecOut(BaseModel):
    id: uuid.UUID
    goods_id: uuid.UUID
    spec_name: str
    price_cents: int
    stock: int
    enabled: bool
    xgj_sku_text: str | None = None
    xgj_outer_id: str | None = None
    sku_bindings: list[SpecSkuBindingOut] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class GoodsXgjProfileIn(BaseModel):
    item_biz_type: int
    sp_biz_type: int
    category_id: int | None = None
    channel_cat_id: str = Field(..., max_length=100)
    original_price_cents: int = 0
    express_fee_cents: int = 0
    stuff_status: int = 0
    notify_url: str | None = Field(None, max_length=2000)
    flash_sale_type: int | None = None
    is_tax_included: bool = False


class GoodsXgjProfileUpdate(BaseModel):
    item_biz_type: int | None = None
    sp_biz_type: int | None = None
    category_id: int | None = None
    channel_cat_id: str | None = Field(None, max_length=100)
    original_price_cents: int | None = None
    express_fee_cents: int | None = None
    stuff_status: int | None = None
    notify_url: str | None = Field(None, max_length=2000)
    flash_sale_type: int | None = None
    is_tax_included: bool | None = None


class GoodsXgjProfileOut(BaseModel):
    item_biz_type: int
    sp_biz_type: int
    category_id: int | None
    channel_cat_id: str
    original_price_cents: int
    express_fee_cents: int
    stuff_status: int
    notify_url: str | None
    flash_sale_type: int | None
    is_tax_included: bool
    product_status: int | None
    publish_status: int | None

    model_config = {"from_attributes": True}


class GoodsXgjPropertyIn(BaseModel):
    property_id: str = Field(..., max_length=100)
    property_name: str = Field(..., max_length=100)
    value_id: str = Field(..., max_length=100)
    value_name: str = Field(..., max_length=100)
    sort_order: int = 0


class GoodsXgjPropertyOut(BaseModel):
    id: uuid.UUID
    property_id: str
    property_name: str
    value_id: str
    value_name: str
    sort_order: int

    model_config = {"from_attributes": True}


class GoodsXgjPublishShopImageIn(BaseModel):
    image_url: str = Field(..., max_length=500)
    sort_order: int = 0


class GoodsXgjPublishShopImageOut(BaseModel):
    id: uuid.UUID
    image_url: str
    sort_order: int

    model_config = {"from_attributes": True}


class GoodsXgjPublishShopIn(BaseModel):
    user_name: str = Field(..., max_length=100)
    province: int
    city: int
    district: int
    title: str = Field(..., max_length=60)
    content: str = Field(..., min_length=5, max_length=5000)
    white_image_url: str | None = Field(None, max_length=500)
    service_support: str | None = Field(None, max_length=200)
    sort_order: int = 0
    images: list[GoodsXgjPublishShopImageIn] = Field(default_factory=list, min_length=1)


class GoodsXgjPublishShopOut(BaseModel):
    id: uuid.UUID
    user_name: str
    province: int
    city: int
    district: int
    title: str
    content: str
    white_image_url: str | None
    service_support: str | None
    sort_order: int
    images: list[GoodsXgjPublishShopImageOut] = []

    model_config = {"from_attributes": True}


class GoodsCreate(BaseModel):
    goods_type: int = Field(..., ge=1, le=3)  # 1=直充 2=卡密 3=券码
    goods_name: str = Field(..., max_length=500)
    logo_url: str | None = None
    price_cents: int = 0
    stock: int = 0
    status: int = Field(1, ge=1, le=2)  # 1=在架 2=下架
    multi_spec: bool = False  # 是否多规格商品
    spec_groups: list[dict] | None = None  # [{name, values}]
    template: dict | None = None
    description: str | None = None
    xgj_profile: GoodsXgjProfileIn
    xgj_properties: list[GoodsXgjPropertyIn] = []
    xgj_publish_shops: list[GoodsXgjPublishShopIn] = Field(..., min_length=1)
    specs: list[GoodsSpecCreate] = []


class GoodsUpdate(BaseModel):
    goods_name: str | None = None
    goods_type: int | None = Field(None, ge=1, le=3)
    logo_url: str | None = None
    price_cents: int | None = None
    stock: int | None = None
    status: int | None = Field(None, ge=1, le=2)
    multi_spec: bool | None = None
    xgj_goods_id: str | None = None
    spec_groups: list[dict] | None = None
    template: dict | None = None
    description: str | None = None
    xgj_profile: GoodsXgjProfileUpdate | None = None
    xgj_properties: list[GoodsXgjPropertyIn] | None = None
    xgj_publish_shops: list[GoodsXgjPublishShopIn] | None = None


class GoodsOut(BaseModel):
    id: uuid.UUID
    goods_no: str
    goods_type: int
    goods_name: str
    logo_url: str | None = None
    price_cents: int
    stock: int
    status: int
    multi_spec: bool = False
    xgj_goods_id: str | None = None
    spec_groups: list[dict] | None = None
    template: dict | None
    description: str | None
    xgj_profile: GoodsXgjProfileOut | None = None
    xgj_properties: list[GoodsXgjPropertyOut] = []
    xgj_publish_shops: list[GoodsXgjPublishShopOut] = []
    specs: list[GoodsSpecOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class XgjOrderOut(BaseModel):
    id: uuid.UUID
    order_no: str
    out_order_no: str
    goods_no: str
    spec_id: uuid.UUID | None
    goods_type: int
    status: int
    quantity: int
    total_price_cents: int
    buyer_info: dict | None
    delivery_info: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── 规格配置（批量设置）─────────────────────────────────────────────
class SpecVariantIn(BaseModel):
    """单个组合变体"""
    spec_name: str = Field(..., max_length=200)
    price_cents: int = 0
    stock: int = 0
    enabled: bool = True
    xgj_sku_text: str | None = None
    xgj_outer_id: str | None = None
    sku_bindings: list[SpecSkuBindingIn] = []


class SpecConfigIn(BaseModel):
    """PUT /goods/{id}/spec-config 整体提交"""
    spec_groups: list[dict] = Field(..., max_length=2)
    variants: list[SpecVariantIn] = []


def validate_spec_groups(groups: list[dict]) -> None:
    """校验规格维度约束，不通过则抛 ValueError。"""
    if len(groups) > 2:
        raise ValueError("最多添加 2 个商品规格")
    for i, g in enumerate(groups):
        name = g.get("name", "")
        values = g.get("values", [])
        if not name or not isinstance(name, str):
            raise ValueError(f"规格 {i+1} 名称不能为空")
        if not isinstance(values, list) or len(values) == 0:
            raise ValueError(f"规格「{name}」至少需要 1 个属性值")
        if len(values) > 150:
            raise ValueError(f"规格「{name}」属性值不能超过 150 个（当前 {len(values)}）")
    if len(groups) == 2:
        v1 = len(groups[0].get("values", []))
        v2 = len(groups[1].get("values", []))
        if v1 * v2 > 400:
            raise ValueError(
                f"两个规格的属性值组合不能超过 400 个（当前 {v1}×{v2}={v1*v2}）"
            )

