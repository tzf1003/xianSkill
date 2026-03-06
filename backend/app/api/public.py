"""Public API — 面向用户 token 使用（AGENT.md §9：/v1/public/...）。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from app.api.schemas import ApiResponse, JobOut, JobSubmit, TokenInfo, SkillOut
from app.core.deps import DbSession
from app.domain.models import Skill
from app.services import job_service, token_service

from sqlalchemy import select

router = APIRouter(prefix="/v1/public", tags=["public"])


@router.get("/token/{token_value}")
async def get_token_info(token_value: str, db: DbSession) -> ApiResponse:
    """查询 token 绑定的 skill 信息、剩余次数、状态、过期时间。"""
    token = await token_service.get_token_by_value(db, token_value)
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    # 加载关联 skill
    stmt = select(Skill).where(Skill.id == token.skill_id)
    result = await db.execute(stmt)
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=500, detail="Skill not found for token")

    # 加载 sku name
    from app.domain.models import SKU
    sku_stmt = select(SKU).where(SKU.id == token.sku_id)
    sku_result = await db.execute(sku_stmt)
    sku = sku_result.scalar_one_or_none()

    info = TokenInfo(
        token=token.token,
        skill=SkillOut.model_validate(skill),
        sku_name=sku.name if sku else "",
        total_uses=token.total_uses,
        remaining=token.remaining,
        status=token.status.value,
        expires_at=token.expires_at,
    )
    return ApiResponse(data=info.model_dump(mode="json"))


@router.post("/job")
async def submit_job(body: JobSubmit, db: DbSession) -> ApiResponse:
    """提交 Job：带 token + inputs + 可选 idempotency_key。"""
    token = await token_service.get_token_by_value(db, body.token)
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    # scope 校验：token 绑定的 skill_id（此处 job 隐含使用 token 绑定的 skill）
    token_service.validate_scope(token)

    job = await job_service.submit_job(
        db,
        token=token,
        idempotency_key=body.idempotency_key,
        inputs=body.inputs,
    )
    await db.commit()
    await db.refresh(job)

    return ApiResponse(data=JobOut.model_validate(job).model_dump(mode="json"))


@router.get("/job/{job_id}")
async def get_job(job_id: uuid.UUID, db: DbSession) -> ApiResponse:
    """查询 Job 状态。"""
    job = await job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return ApiResponse(data=JobOut.model_validate(job).model_dump(mode="json"))
