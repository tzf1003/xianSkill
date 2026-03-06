"""Admin API — 最小管理（AGENT.md §9：/v1/admin/...）。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.schemas import (
    ApiResponse,
    JobOut,
    OrderCreate,
    OrderOut,
    SKUCreate,
    SKUOut,
    SkillCreate,
    SkillOut,
)
from app.core.deps import DbSession
from app.domain.models import Order, Skill, SkillType, SKU, DeliveryMode
from app.services import job_service, token_service

router = APIRouter(prefix="/v1/admin", tags=["admin"])


@router.post("/skills")
async def create_skill(body: SkillCreate, db: DbSession) -> ApiResponse:
    """创建 Skill（存 manifest）。"""
    skill = Skill(
        name=body.name,
        description=body.description,
        type=SkillType(body.type),
        version=body.version,
        input_schema=body.input_schema,
        output_schema=body.output_schema,
    )
    db.add(skill)
    await db.commit()
    await db.refresh(skill)
    return ApiResponse(data=SkillOut.model_validate(skill).model_dump(mode="json"))


@router.post("/skus")
async def create_sku(body: SKUCreate, db: DbSession) -> ApiResponse:
    """创建 SKU。"""
    # 校验 skill 存在
    stmt = select(Skill).where(Skill.id == body.skill_id)
    result = await db.execute(stmt)
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    sku = SKU(
        skill_id=body.skill_id,
        name=body.name,
        price_cents=body.price_cents,
        delivery_mode=DeliveryMode(body.delivery_mode),
        total_uses=body.total_uses,
    )
    db.add(sku)
    await db.commit()
    await db.refresh(sku)
    return ApiResponse(data=SKUOut.model_validate(sku).model_dump(mode="json"))


@router.post("/orders")
async def create_order(body: OrderCreate, db: DbSession) -> ApiResponse:
    """创建订单并自动生成 token，返回 token URL。"""
    # 校验 SKU 存在并获取关联信息
    stmt = select(SKU).where(SKU.id == body.sku_id)
    result = await db.execute(stmt)
    sku = result.scalar_one_or_none()
    if not sku:
        raise HTTPException(status_code=404, detail="SKU not found")

    order = Order(
        sku_id=body.sku_id,
        channel=body.channel,
    )
    db.add(order)
    await db.flush()  # 获取 order.id

    token = await token_service.create_token(
        db,
        order_id=order.id,
        sku_id=sku.id,
        skill_id=sku.skill_id,
        total_uses=sku.total_uses,
    )
    await db.commit()
    await db.refresh(order)
    await db.refresh(token)

    out = OrderOut(
        id=order.id,
        sku_id=order.sku_id,
        status=order.status.value,
        channel=order.channel,
        token_url=f"/v1/public/token/{token.token}",
        created_at=order.created_at,
    )
    return ApiResponse(data=out.model_dump(mode="json"))


@router.post("/jobs/{job_id}/finalize")
async def finalize_job(
    job_id: uuid.UUID,
    db: DbSession,
    success: bool = True,
    error: str | None = None,
) -> ApiResponse:
    """手动 finalize Job（M1 测试用）。"""
    job = await job_service.finalize_job(db, job_id, success=success, error=error)
    await db.commit()
    await db.refresh(job)
    return ApiResponse(data=JobOut.model_validate(job).model_dump(mode="json"))
