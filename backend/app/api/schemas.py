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


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    cover_url: str | None = None
    type: str | None = None
    options: dict | None = None
    enabled: bool | None = None


class ProjectOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    cover_url: str | None
    type: str
    options: dict | None
    enabled: bool
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
    project_id: uuid.UUID | None = None


class SkillOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    type: str
    version: str
    enabled: bool
    project_id: uuid.UUID | None = None
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
    project_id: uuid.UUID | None = None
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

