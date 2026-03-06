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
    created_at: datetime

    model_config = {"from_attributes": True}


# ── SKU ───────────────────────────────────────────────────────────────
class SKUCreate(BaseModel):
    skill_id: uuid.UUID
    name: str = Field(..., max_length=200)
    price_cents: int = 0
    delivery_mode: str = Field("auto", pattern=r"^(auto|human)$")
    total_uses: int = Field(1, ge=1)


class SKUOut(BaseModel):
    id: uuid.UUID
    skill_id: uuid.UUID
    name: str
    price_cents: int
    delivery_mode: str
    total_uses: int
    enabled: bool
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
class TokenInfo(BaseModel):
    token: str
    skill: SkillOut
    sku_name: str
    total_uses: int
    remaining: int
    status: str
    expires_at: datetime | None

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
