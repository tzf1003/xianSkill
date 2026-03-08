"""Admin API — 完整后台管理（AGENT.md §9：/v1/admin/...）。"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.schemas import (
    ApiResponse,
    DeliveryRecordOut,
    GoodsCreate,
    GoodsOut,
    GoodsSpecCreate,
    GoodsSpecOut,
    GoodsSpecUpdate,
    GoodsUpdate,
    JobOut,
    OrderCreate,
    OrderOut,
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
    SKUCreate,
    SKUOut,
    SKUUpdate,
    SkillCreate,
    SkillOut,
    SkillUpdate,
    SpecSkuBindingIn,
    SpecSkuBindingOut,
    SpecConfigIn,
    StatsOut,
    TokenCreate,
    TokenOut,
    WebhookCreate,
    WebhookOut,
    XgjShopOut,
    XgjGoodsSyncOut,
    XgjShopSyncOut,
    XgjOrderOut,
    validate_spec_groups,
)
from app.core.config import settings
from app.core.deps import DbSession, create_admin_token, require_admin, get_storage
from app.domain.models import (
    Asset,
    DeliveryRecord,
    DeliveryMode,
    DeliveryTiming,
    Goods,
    GoodsSpec,
    GoodsXgjProfile,
    GoodsXgjProperty,
    GoodsXgjPublishShop,
    GoodsXgjPublishShopImage,
    GoodsSubscription,
    Job,
    JobStatus,
    Order,
    Project,
    SKU,
    Skill,
    SkillType,
    SpecSkuBinding,
    Token,
    TokenStatus,
    Webhook,
    XgjShop,
    XgjOrder,
)
from app.infra.xgj.base_client import XGJApiError
from app.infra.xgj.erp_client import XGJErpClient
from app.services import job_service, token_service
from app.api.admin_routes.xgj_support import sync_xgj_goods as _sync_xgj_goods_from_cloud

# ── 登录路由（无需鉴权）──────────────────────────────────────────────
auth_router = APIRouter(prefix="/v1/admin", tags=["admin-auth"])


class _LoginIn(BaseModel):
    username: str
    password: str


@auth_router.post("/login")
async def admin_login(body: _LoginIn) -> ApiResponse:
    """管理员登录，成功返回 session token。"""
    if body.username != settings.ADMIN_USERNAME or body.password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="账号或密码错误")
    return ApiResponse(data={"token": create_admin_token()})


# ── 受保护的管理路由 ──────────────────────────────────────────────────
router = APIRouter(
    prefix="/v1/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


# ═══════════════════════════════════════════════════════════════════════
# Stats
# ═══════════════════════════════════════════════════════════════════════

@router.get("/stats")
async def get_stats(db: DbSession) -> ApiResponse:
    """仪表盘统计数据。"""
    async def count(model):
        r = await db.execute(select(func.count()).select_from(model))
        return r.scalar_one()

    async def count_jobs_by_status(status: JobStatus):
        r = await db.execute(
            select(func.count()).select_from(Job).where(Job.status == status)
        )
        return r.scalar_one()

    stats = StatsOut(
        total_skills=await count(Skill),
        total_skus=await count(SKU),
        total_orders=await count(Order),
        total_tokens=await count(Token),
        total_jobs=await count(Job),
        jobs_queued=await count_jobs_by_status(JobStatus.queued),
        jobs_running=await count_jobs_by_status(JobStatus.running),
        jobs_succeeded=await count_jobs_by_status(JobStatus.succeeded),
        jobs_failed=await count_jobs_by_status(JobStatus.failed),
    )
    return ApiResponse(data=stats.model_dump())


# ═══════════════════════════════════════════════════════════════════════
# Projects
# ═══════════════════════════════════════════════════════════════════════

@router.get("/projects")
async def list_projects(
    db: DbSession,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ApiResponse:
    result = await db.execute(
        select(Project).order_by(Project.created_at.desc()).limit(limit).offset(offset)
    )
    projects = result.scalars().all()
    total = (await db.execute(select(func.count()).select_from(Project))).scalar_one()
    return ApiResponse(data={
        "total": total,
        "items": [ProjectOut.model_validate(p).model_dump(mode="json") for p in projects],
    })


@router.post("/projects")
async def create_project(body: ProjectCreate, db: DbSession) -> ApiResponse:
    existing = (await db.execute(select(Project).where(Project.slug == body.slug))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail=f"Slug '{body.slug}' already exists")
    project = Project(
        name=body.name,
        slug=body.slug,
        description=body.description,
        cover_url=body.cover_url,
        type=body.type,
        options=body.options.model_dump(exclude_none=True) if body.options else None,
        skill_id=body.skill_id,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return ApiResponse(data=ProjectOut.model_validate(project).model_dump(mode="json"))


@router.get("/projects/{project_id}")
async def get_project(project_id: uuid.UUID, db: DbSession) -> ApiResponse:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ApiResponse(data=ProjectOut.model_validate(project).model_dump(mode="json"))


@router.patch("/projects/{project_id}")
async def update_project(project_id: uuid.UUID, body: ProjectUpdate, db: DbSession) -> ApiResponse:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "options" and isinstance(value, BaseModel):
            value = value.model_dump(exclude_none=True)
        setattr(project, field, value)
    await db.commit()
    await db.refresh(project)
    return ApiResponse(data=ProjectOut.model_validate(project).model_dump(mode="json"))


@router.delete("/projects/{project_id}")
async def delete_project(project_id: uuid.UUID, db: DbSession) -> ApiResponse:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(project)
    await db.commit()
    return ApiResponse(data={"deleted": str(project_id)})


# ═══════════════════════════════════════════════════════════════════════
# Skills
# ═══════════════════════════════════════════════════════════════════════

@router.get("/skills")
async def list_skills(
    db: DbSession,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ApiResponse:
    result = await db.execute(
        select(Skill).order_by(Skill.created_at.desc()).limit(limit).offset(offset)
    )
    skills = result.scalars().all()
    total = (await db.execute(select(func.count()).select_from(Skill))).scalar_one()
    return ApiResponse(data={
        "total": total,
        "items": [SkillOut.model_validate(s).model_dump(mode="json") for s in skills],
    })


@router.post("/skills")
async def create_skill(body: SkillCreate, db: DbSession) -> ApiResponse:
    skill = Skill(
        name=body.name,
        description=body.description,
        type=SkillType(body.type),
        version=body.version,
        input_schema=body.input_schema,
        output_schema=body.output_schema,
        prompt_template=body.prompt_template,
        runner_config=body.runner_config,
    )
    db.add(skill)
    await db.commit()
    await db.refresh(skill)
    return ApiResponse(data=SkillOut.model_validate(skill).model_dump(mode="json"))


@router.get("/skills/{skill_id}")
async def get_skill(skill_id: uuid.UUID, db: DbSession) -> ApiResponse:
    skill = await db.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return ApiResponse(data=SkillOut.model_validate(skill).model_dump(mode="json"))


@router.put("/skills/{skill_id}")
async def update_skill(skill_id: uuid.UUID, body: SkillUpdate, db: DbSession) -> ApiResponse:
    skill = await db.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    updates = body.model_dump(exclude_none=True)
    for key, val in updates.items():
        setattr(skill, key, val)
    await db.commit()
    await db.refresh(skill)
    return ApiResponse(data=SkillOut.model_validate(skill).model_dump(mode="json"))


@router.delete("/skills/{skill_id}")
async def disable_skill(skill_id: uuid.UUID, db: DbSession) -> ApiResponse:
    """软删除：设 enabled=False。"""
    skill = await db.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    skill.enabled = False
    await db.commit()
    return ApiResponse(data={"id": str(skill_id), "enabled": False})


# ═══════════════════════════════════════════════════════════════════════
# SKUs
# ═══════════════════════════════════════════════════════════════════════

@router.get("/skus")
async def list_skus(
    db: DbSession,
    skill_id: uuid.UUID | None = Query(None),
    project_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ApiResponse:
    stmt = select(SKU).order_by(SKU.created_at.desc())
    if skill_id:
        stmt = stmt.where(SKU.skill_id == skill_id)
    if project_id:
        stmt = stmt.where(SKU.project_id == project_id)
    result = await db.execute(stmt.limit(limit).offset(offset))
    skus = result.scalars().all()
    count_stmt = select(func.count()).select_from(SKU)
    if skill_id:
        count_stmt = count_stmt.where(SKU.skill_id == skill_id)
    if project_id:
        count_stmt = count_stmt.where(SKU.project_id == project_id)
    total = (await db.execute(count_stmt)).scalar_one()
    return ApiResponse(data={
        "total": total,
        "items": [SKUOut.model_validate(s).model_dump(mode="json") for s in skus],
    })


@router.post("/skus")
async def create_sku(body: SKUCreate, db: DbSession) -> ApiResponse:
    skill = await db.get(Skill, body.skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    sku = SKU(
        skill_id=body.skill_id,
        name=body.name,
        price_cents=body.price_cents,
        delivery_mode=DeliveryMode(body.delivery_mode),
        total_uses=body.total_uses,
        human_sla_hours=body.human_sla_hours,
        human_price_cents=body.human_price_cents,
        project_id=body.project_id,
    )
    db.add(sku)
    await db.commit()
    await db.refresh(sku)
    return ApiResponse(data=SKUOut.model_validate(sku).model_dump(mode="json"))


@router.get("/skus/{sku_id}")
async def get_sku(sku_id: uuid.UUID, db: DbSession) -> ApiResponse:
    sku = await db.get(SKU, sku_id)
    if not sku:
        raise HTTPException(status_code=404, detail="SKU not found")
    return ApiResponse(data=SKUOut.model_validate(sku).model_dump(mode="json"))


@router.put("/skus/{sku_id}")
async def update_sku(sku_id: uuid.UUID, body: SKUUpdate, db: DbSession) -> ApiResponse:
    sku = await db.get(SKU, sku_id)
    if not sku:
        raise HTTPException(status_code=404, detail="SKU not found")
    updates = body.model_dump(exclude_none=True)
    if "delivery_mode" in updates:
        updates["delivery_mode"] = DeliveryMode(updates["delivery_mode"])
    for key, val in updates.items():
        setattr(sku, key, val)
    await db.commit()
    await db.refresh(sku)
    return ApiResponse(data=SKUOut.model_validate(sku).model_dump(mode="json"))


# ═══════════════════════════════════════════════════════════════════════
# Orders
# ═══════════════════════════════════════════════════════════════════════

@router.get("/orders")
async def list_orders(
    db: DbSession,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ApiResponse:
    result = await db.execute(
        select(Order).order_by(Order.created_at.desc()).limit(limit).offset(offset)
    )
    orders = result.scalars().all()
    total = (await db.execute(select(func.count()).select_from(Order))).scalar_one()
    return ApiResponse(data={
        "total": total,
        "items": [OrderOut.model_validate(o).model_dump(mode="json") for o in orders],
    })


@router.post("/orders")
async def create_order(body: OrderCreate, db: DbSession) -> ApiResponse:
    sku = await db.get(SKU, body.sku_id)
    if not sku:
        raise HTTPException(status_code=404, detail="SKU not found")

    order = Order(sku_id=body.sku_id, channel=body.channel)
    db.add(order)
    await db.flush()

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

    # 订单创建即表示付款（paid），异步触发 webhook
    skill = await db.get(Skill, sku.skill_id)
    if skill:
        asyncio.create_task(_fire_order_paid(db, order=order, token=token, sku=sku, skill=skill))

    out = OrderOut(
        id=order.id,
        sku_id=order.sku_id,
        status=order.status.value,
        channel=order.channel,
        token_url=f"/s/{token.token}",
        created_at=order.created_at,
    )
    return ApiResponse(data=out.model_dump(mode="json"))


async def _fire_order_paid(db, *, order, token, sku, skill) -> None:
    """Webhook 广播（后台任务，不阻塞响应）。"""
    try:
        from app.infra.webhook import fire_order_paid
        await fire_order_paid(
            db,
            order=order,
            token=token,
            sku=sku,
            skill=skill,
            base_url=settings.BASE_URL,
        )
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("webhook fire failed: %s", exc)


@router.get("/orders/{order_id}")
async def get_order(order_id: uuid.UUID, db: DbSession) -> ApiResponse:
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    # 查找关联 token
    token_result = await db.execute(
        select(Token).where(Token.order_id == order_id)
    )
    token = token_result.scalar_one_or_none()
    out = OrderOut(
        id=order.id,
        sku_id=order.sku_id,
        status=order.status.value,
        channel=order.channel,
        token_url=f"/s/{token.token}" if token else None,
        created_at=order.created_at,
    )
    return ApiResponse(data=out.model_dump(mode="json"))


# ═══════════════════════════════════════════════════════════════════════
# Tokens
# ═══════════════════════════════════════════════════════════════════════

@router.get("/tokens")
async def list_tokens(
    db: DbSession,
    status: str | None = Query(None),
    project_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ApiResponse:
    stmt = select(Token).order_by(Token.created_at.desc())
    if status:
        try:
            stmt = stmt.where(Token.status == TokenStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    if project_id:
        stmt = stmt.join(SKU, Token.sku_id == SKU.id).where(SKU.project_id == project_id)
    result = await db.execute(stmt.limit(limit).offset(offset))
    tokens = result.scalars().all()
    count_stmt = select(func.count()).select_from(Token)
    if status:
        count_stmt = count_stmt.where(Token.status == TokenStatus(status))
    if project_id:
        count_stmt = count_stmt.join(SKU, Token.sku_id == SKU.id).where(SKU.project_id == project_id)
    total = (await db.execute(count_stmt)).scalar_one()
    items = []
    for t in tokens:
        items.append(TokenOut(
            id=t.id,
            token=t.token,
            order_id=t.order_id,
            sku_id=t.sku_id,
            skill_id=t.skill_id,
            status=t.status.value,
            total_uses=t.total_uses,
            used_count=t.used_count,
            reserved_count=t.reserved_count,
            remaining=t.remaining,
            expires_at=t.expires_at,
            created_at=t.created_at,
        ).model_dump(mode="json"))
    return ApiResponse(data={"total": total, "items": items})


@router.delete("/tokens/{token_id}")
async def revoke_token(token_id: uuid.UUID, db: DbSession) -> ApiResponse:
    """撤销 token，使其无法再提交 Job。"""
    token = await db.get(Token, token_id)
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    token.status = TokenStatus.revoked
    await db.commit()
    return ApiResponse(data={"id": str(token_id), "status": "revoked"})


@router.post("/tokens")
async def create_token_direct(body: TokenCreate, db: DbSession) -> ApiResponse:
    """手动创建 Token（自动建立 manual 订单，无需走下单流程）。"""
    sku = await db.get(SKU, body.sku_id)
    if not sku:
        raise HTTPException(status_code=404, detail="SKU not found")

    # 自动创建 manual 订单
    order = Order(sku_id=body.sku_id, channel=body.channel or "manual")
    db.add(order)
    await db.flush()

    uses = body.total_uses if body.total_uses is not None else sku.total_uses
    token = await token_service.create_token(
        db,
        order_id=order.id,
        sku_id=sku.id,
        skill_id=sku.skill_id,
        total_uses=uses,
        expires_at=body.expires_at,
    )
    await db.commit()
    await db.refresh(token)

    out = TokenOut(
        id=token.id,
        token=token.token,
        order_id=token.order_id,
        sku_id=token.sku_id,
        skill_id=token.skill_id,
        status=token.status.value,
        total_uses=token.total_uses,
        used_count=token.used_count,
        reserved_count=token.reserved_count,
        remaining=token.remaining,
        expires_at=token.expires_at,
        created_at=token.created_at,
    )
    return ApiResponse(data=out.model_dump(mode="json"))


# ═══════════════════════════════════════════════════════════════════════
# Jobs
# ═══════════════════════════════════════════════════════════════════════

@router.get("/jobs")
async def list_jobs(
    db: DbSession,
    status: str | None = Query(None),
    skill_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ApiResponse:
    from app.infra.storage import StorageService
    stmt = select(Job).order_by(Job.created_at.desc())
    if status:
        try:
            stmt = stmt.where(Job.status == JobStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    if skill_id:
        stmt = stmt.where(Job.skill_id == skill_id)
    result = await db.execute(stmt.limit(limit).offset(offset))
    jobs = result.scalars().all()
    count_stmt = select(func.count()).select_from(Job)
    if status:
        count_stmt = count_stmt.where(Job.status == JobStatus(status))
    if skill_id:
        count_stmt = count_stmt.where(Job.skill_id == skill_id)
    total = (await db.execute(count_stmt)).scalar_one()
    from app.api.public import _job_out
    try:
        storage = StorageService()
    except Exception:
        storage = None
    return ApiResponse(data={
        "total": total,
        "items": [_job_out(j, storage).model_dump(mode="json") for j in jobs],
    })


@router.get("/jobs/{job_id}")
async def get_job(job_id: uuid.UUID, db: DbSession) -> ApiResponse:
    from app.infra.storage import StorageService
    from app.api.public import _job_out
    job = await job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        storage = StorageService()
    except Exception:
        storage = None
    return ApiResponse(data=_job_out(job, storage).model_dump(mode="json"))


@router.post("/jobs/{job_id}/retry")
async def retry_job(
    job_id: uuid.UUID,
    db: DbSession,
    background_tasks: BackgroundTasks,
) -> ApiResponse:
    """手动重新触发 Job 执行（queued/running/failed 均可重试）。"""
    from app.tasks.execute_job import run_job
    from datetime import datetime, timezone

    job = await job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status == JobStatus.succeeded:
        raise HTTPException(status_code=409, detail="Job already succeeded")

    # 重置为 queued 状态
    job.status = JobStatus.queued
    job.started_at = None
    job.finished_at = None
    job.error = None
    job.log_text = None
    await db.commit()
    await db.refresh(job)

    background_tasks.add_task(run_job, str(job.id))
    return ApiResponse(data=JobOut.model_validate(job).model_dump(mode="json"))


@router.post("/jobs/{job_id}/finalize")
async def finalize_job(
    job_id: uuid.UUID,
    db: DbSession,
    success: bool = True,
    error: str | None = None,
) -> ApiResponse:
    """手动 finalize Job。"""
    job = await job_service.finalize_job(db, job_id, success=success, error=error)
    await db.commit()
    await db.refresh(job)
    return ApiResponse(data=JobOut.model_validate(job).model_dump(mode="json"))


# ═══════════════════════════════════════════════════════════════════════
# Human Delivery
# ═══════════════════════════════════════════════════════════════════════

@router.post("/jobs/{job_id}/human-deliver")
async def human_deliver(
    job_id: uuid.UUID,
    db: DbSession,
    operator: str = Form(..., description="操作人姓名"),
    notes: str | None = Form(None, description="备注"),
    file: UploadFile = File(..., description="交付产物文件"),
) -> ApiResponse:
    """人工交付：上传产物文件，标记 Job 为 succeeded 并 finalize token 扣次。

    审计要求（AGENT.md §6）：记录操作人、时间戳、产物 hash。
    """
    from app.infra.storage import StorageService
    from app.api.public import _job_out

    job = await job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in (JobStatus.queued, JobStatus.running):
        raise HTTPException(
            status_code=409,
            detail=f"Job already in terminal state: {job.status.value}",
        )

    # 读文件 + 计 hash
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    output_hash = hashlib.sha256(data).hexdigest()

    # 上传到对象存储
    try:
        storage = StorageService()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Storage unavailable: {exc}")

    safe_name = (file.filename or "delivery").replace(" ", "_")
    storage_key = f"deliveries/{job_id}/{safe_name}"
    storage.put_bytes(storage_key, data, file.content_type or "application/octet-stream")

    # 创建 Asset 记录
    asset = Asset(
        job_id=job_id,
        filename=safe_name,
        storage_key=storage_key,
        content_type=file.content_type,
        size_bytes=len(data),
        hash=output_hash,
    )
    db.add(asset)

    # 创建 DeliveryRecord（审计证据）
    record = DeliveryRecord(
        job_id=job_id,
        operator=operator,
        notes=notes,
        output_hash=output_hash,
    )
    db.add(record)

    # 通过 job_service 做状态机流转 + token finalize
    await db.flush()
    job = await job_service.finalize_job(
        db, job_id, success=True, result={"delivered_by": operator}
    )
    await db.commit()
    await db.refresh(job)

    return ApiResponse(data=_job_out(job, storage).model_dump(mode="json"))


@router.get("/jobs/{job_id}/delivery-record")
async def get_delivery_record(job_id: uuid.UUID, db: DbSession) -> ApiResponse:
    """查询指定 Job 的人工交付记录（审计证据）。"""
    result = await db.execute(
        select(DeliveryRecord).where(DeliveryRecord.job_id == job_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Delivery record not found")
    return ApiResponse(data=DeliveryRecordOut.model_validate(record).model_dump(mode="json"))


# ═══════════════════════════════════════════════════════════════════════
# Webhooks
# ═══════════════════════════════════════════════════════════════════════

@router.get("/webhooks")
async def list_webhooks(db: DbSession) -> ApiResponse:
    """列出所有 webhook 配置（不返回 secret）。"""
    result = await db.execute(select(Webhook).order_by(Webhook.created_at.desc()))
    webhooks = result.scalars().all()
    return ApiResponse(data={
        "items": [WebhookOut.model_validate(w).model_dump(mode="json") for w in webhooks],
    })


@router.post("/webhooks")
async def create_webhook(body: WebhookCreate, db: DbSession) -> ApiResponse:
    """注册一个新的 webhook endpoint。"""
    wh = Webhook(
        url=body.url,
        secret=body.secret,
        events=body.events,
        description=body.description,
    )
    db.add(wh)
    await db.commit()
    await db.refresh(wh)
    return ApiResponse(data=WebhookOut.model_validate(wh).model_dump(mode="json"))


@router.put("/webhooks/{webhook_id}")
async def update_webhook(
    webhook_id: uuid.UUID,
    body: WebhookCreate,
    db: DbSession,
) -> ApiResponse:
    """更新 webhook 配置。"""
    wh = await db.get(Webhook, webhook_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")
    wh.url = body.url
    wh.secret = body.secret
    wh.events = body.events
    wh.description = body.description
    await db.commit()
    await db.refresh(wh)
    return ApiResponse(data=WebhookOut.model_validate(wh).model_dump(mode="json"))


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: uuid.UUID, db: DbSession) -> ApiResponse:
    """删除 webhook 配置。"""
    wh = await db.get(Webhook, webhook_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")
    await db.delete(wh)
    await db.commit()
    return ApiResponse(data={"id": str(webhook_id), "deleted": True})


@router.post("/webhooks/{webhook_id}/disable")
async def disable_webhook(webhook_id: uuid.UUID, db: DbSession) -> ApiResponse:
    """临时禁用某个 webhook（不删除）。"""
    wh = await db.get(Webhook, webhook_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")
    wh.enabled = False
    await db.commit()
    return ApiResponse(data={"id": str(webhook_id), "enabled": False})


# ═══════════════════════════════════════════════════════════════════════
# Shops（闲管家店铺管理）
# ═══════════════════════════════════════════════════════════════════════

@router.get("/shops")
async def list_xgj_shops(
    db: DbSession,
    valid_only: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ApiResponse:
    stmt = select(XgjShop).order_by(XgjShop.is_valid.desc(), XgjShop.updated_at.desc())
    count_stmt = select(func.count()).select_from(XgjShop)
    if valid_only is not None:
        stmt = stmt.where(XgjShop.is_valid == valid_only)
        count_stmt = count_stmt.where(XgjShop.is_valid == valid_only)
    result = await db.execute(stmt.limit(limit).offset(offset))
    items = result.scalars().all()
    total = (await db.execute(count_stmt)).scalar_one()
    return ApiResponse(data={
        "total": total,
        "items": [XgjShopOut.model_validate(shop).model_dump(mode="json") for shop in items],
    })


@router.post("/shops/sync")
async def sync_xgj_shops(db: DbSession) -> ApiResponse:
    result = await _sync_xgj_shops(db)
    return ApiResponse(data=result.model_dump())


# ═══════════════════════════════════════════════════════════════════════
# Goods（虚拟货源商品管理）
# ═══════════════════════════════════════════════════════════════════════

@router.get("/goods")
async def list_goods(
    db: DbSession,
    status: int | None = Query(None, ge=1, le=2),
    goods_type: int | None = Query(None, ge=1, le=3),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ApiResponse:
    stmt = select(Goods).options(
        selectinload(Goods.xgj_profile),
        selectinload(Goods.xgj_properties),
        selectinload(Goods.xgj_publish_shops).selectinload(GoodsXgjPublishShop.images),
        selectinload(Goods.xgj_publish_shops).selectinload(GoodsXgjPublishShop.xgj_shop),
        selectinload(Goods.specs).selectinload(GoodsSpec.sku_bindings),
    ).order_by(Goods.created_at.desc())
    if status is not None:
        stmt = stmt.where(Goods.status == status)
    if goods_type is not None:
        stmt = stmt.where(Goods.goods_type == goods_type)
    result = await db.execute(stmt.limit(limit).offset(offset))
    items = result.scalars().all()
    count_stmt = select(func.count()).select_from(Goods)
    if status is not None:
        count_stmt = count_stmt.where(Goods.status == status)
    if goods_type is not None:
        count_stmt = count_stmt.where(Goods.goods_type == goods_type)
    total = (await db.execute(count_stmt)).scalar_one()
    return ApiResponse(data={
        "total": total,
        "items": [GoodsOut.model_validate(g).model_dump(mode="json") for g in items],
    })


async def _load_goods_full(db: DbSession, goods_id: uuid.UUID) -> Goods:
    result = await db.execute(
        select(Goods)
        .where(Goods.id == goods_id)
        .options(
            selectinload(Goods.xgj_profile),
            selectinload(Goods.xgj_properties),
            selectinload(Goods.xgj_publish_shops).selectinload(GoodsXgjPublishShop.images),
            selectinload(Goods.xgj_publish_shops).selectinload(GoodsXgjPublishShop.xgj_shop),
            selectinload(Goods.specs).selectinload(GoodsSpec.sku_bindings),
        )
    )
    goods = result.scalar_one_or_none()
    if not goods:
        raise HTTPException(status_code=404, detail="商品不存在")
    return goods


def _get_erp_client() -> XGJErpClient:
    return XGJErpClient(
        app_key=settings.XGJ_ERP_APP_KEY,
        app_secret=settings.XGJ_ERP_APP_SECRET,
    )


def _normalize_xgj_shop_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        shops = payload.get("list")
        if isinstance(shops, list):
            return [item for item in shops if isinstance(item, dict)]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    raise HTTPException(status_code=502, detail="闲管家店铺返回结构异常")


def _to_int(value: Any, *, required: bool = False, field_name: str = "") -> int | None:
    if value is None or value == "":
        if required:
            raise HTTPException(status_code=502, detail=f"闲管家店铺字段缺失: {field_name}")
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        if required:
            raise HTTPException(status_code=502, detail=f"闲管家店铺字段格式错误: {field_name}")
        return None


def _sync_xgj_shop_entity(shop: XgjShop, data: dict[str, Any]) -> None:
    shop.authorize_expires = _to_int(data.get("authorize_expires"), required=True, field_name="authorize_expires") or 0
    shop.user_id = _to_int(data.get("user_id"), field_name="user_id")
    shop.user_identity = str(data.get("user_identity") or "")
    shop.user_name = str(data.get("user_name") or "")
    shop.user_nick = str(data.get("user_nick") or "")
    shop.shop_name = str(data.get("shop_name") or "")
    shop.service_support = data.get("service_support") or None
    shop.is_deposit_enough = bool(data.get("is_deposit_enough", False))
    shop.is_pro = bool(data.get("is_pro", False))
    shop.is_valid = bool(data.get("is_valid", False))
    shop.is_trial = bool(data.get("is_trial", False))
    shop.valid_start_time = _to_int(data.get("valid_start_time"), field_name="valid_start_time")
    shop.valid_end_time = _to_int(data.get("valid_end_time"), required=True, field_name="valid_end_time") or 0
    shop.item_biz_types = str(data.get("item_biz_types") or "")

    missing = [
        name
        for name, value in (
            ("user_identity", shop.user_identity),
            ("user_name", shop.user_name),
            ("user_nick", shop.user_nick),
            ("shop_name", shop.shop_name),
            ("item_biz_types", shop.item_biz_types),
        )
        if not value
    ]
    if missing:
        raise HTTPException(status_code=502, detail=f"闲管家店铺字段缺失: {', '.join(missing)}")


async def _sync_xgj_shops(db: DbSession) -> XgjShopSyncOut:
    if not settings.XGJ_ERP_APP_KEY or not settings.XGJ_ERP_APP_SECRET:
        raise HTTPException(status_code=503, detail="未配置闲管家 ERP 凭证")

    try:
        async with _get_erp_client() as client:
            payload = await client.get_shops()
    except XGJApiError as exc:
        raise HTTPException(status_code=502, detail=f"同步闲管家店铺失败: {exc.msg}")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"同步闲管家店铺失败: {exc}")

    remote_items = _normalize_xgj_shop_list(payload)
    existing_result = await db.execute(select(XgjShop))
    existing_shops = existing_result.scalars().all()
    existing_by_authorize_id = {shop.authorize_id: shop for shop in existing_shops}
    remote_ids: set[int] = set()
    created = 0
    updated = 0

    for item in remote_items:
        authorize_id = _to_int(item.get("authorize_id"), required=True, field_name="authorize_id")
        assert authorize_id is not None
        remote_ids.add(authorize_id)
        shop = existing_by_authorize_id.get(authorize_id)
        if shop is None:
            shop = XgjShop(authorize_id=authorize_id)
            db.add(shop)
            created += 1
        else:
            updated += 1
        _sync_xgj_shop_entity(shop, item)

    deleted = 0
    for shop in existing_shops:
        if shop.authorize_id not in remote_ids:
            await db.delete(shop)
            deleted += 1

    await db.commit()
    return XgjShopSyncOut(
        synced=len(remote_items),
        created=created,
        updated=updated,
        deleted=deleted,
    )


def _build_xgj_sku_text(goods: Goods, spec: GoodsSpec) -> str:
    if spec.xgj_sku_text:
        return spec.xgj_sku_text
    if not goods.spec_groups:
        return spec.spec_name
    parts = [part.strip() for part in spec.spec_name.split("/")]
    if len(parts) != len(goods.spec_groups):
        return spec.spec_name
    return ";".join(
        f"{group.get('name', '')}:{value}"
        for group, value in zip(goods.spec_groups, parts)
        if group.get("name") and value
    ) or spec.spec_name


def _apply_xgj_profile(goods: Goods, profile_data: Any, *, partial: bool) -> None:
    if profile_data is None:
        return

    fields = [
        "item_biz_type",
        "sp_biz_type",
        "category_id",
        "channel_cat_id",
        "original_price_cents",
        "express_fee_cents",
        "stuff_status",
        "notify_url",
        "flash_sale_type",
        "is_tax_included",
    ]
    payload = profile_data.model_dump(exclude_unset=partial)
    profile = goods.xgj_profile
    if profile is None:
        current = {key: payload.get(key) for key in fields}
        missing = [key for key in ("item_biz_type", "sp_biz_type", "channel_cat_id") if not current.get(key)]
        if missing:
            raise HTTPException(status_code=422, detail=f"闲管家配置缺少字段: {', '.join(missing)}")
        goods.xgj_profile = GoodsXgjProfile(goods_id=goods.id, **current)
        return

    for key, value in payload.items():
        setattr(profile, key, value)


def _replace_xgj_properties(goods: Goods, properties: list[Any]) -> None:
    goods.xgj_properties = [
        GoodsXgjProperty(
            property_id=item.property_id,
            property_name=item.property_name,
            value_id=item.value_id,
            value_name=item.value_name,
            sort_order=item.sort_order if item.sort_order is not None else index,
        )
        for index, item in enumerate(properties)
    ]


async def _replace_xgj_publish_shops(db: DbSession, goods: Goods, shops: list[Any]) -> None:
    selected_shop_ids = [shop_in.xgj_shop_id for shop_in in shops if getattr(shop_in, "xgj_shop_id", None)]
    if len(selected_shop_ids) != len(set(selected_shop_ids)):
        raise HTTPException(status_code=422, detail="闲管家发布店铺不能重复选择同一个本地店铺")

    xgj_shops_by_id: dict[uuid.UUID, XgjShop] = {}
    if selected_shop_ids:
        result = await db.execute(select(XgjShop).where(XgjShop.id.in_(selected_shop_ids)))
        xgj_shops_by_id = {shop.id: shop for shop in result.scalars().all()}
        if len(xgj_shops_by_id) != len(selected_shop_ids):
            raise HTTPException(status_code=422, detail="所选本地店铺不存在或已被删除")

    goods.xgj_publish_shops = []
    for shop_index, shop_in in enumerate(shops):
        linked_shop = xgj_shops_by_id.get(shop_in.xgj_shop_id) if getattr(shop_in, "xgj_shop_id", None) else None
        shop = GoodsXgjPublishShop(
            xgj_shop_id=shop_in.xgj_shop_id,
            user_name=shop_in.user_name,
            province=shop_in.province,
            city=shop_in.city,
            district=shop_in.district,
            title=shop_in.title,
            content=shop_in.content,
            white_image_url=shop_in.white_image_url,
            service_support=shop_in.service_support or (linked_shop.service_support if linked_shop else None),
            sort_order=shop_in.sort_order if shop_in.sort_order is not None else shop_index,
            images=[
                GoodsXgjPublishShopImage(
                    image_url=image.image_url,
                    sort_order=image.sort_order if image.sort_order is not None else image_index,
                )
                for image_index, image in enumerate(shop_in.images)
            ],
        )
        if linked_shop is not None:
            shop.user_name = linked_shop.user_name
        goods.xgj_publish_shops.append(shop)


def _build_xgj_publish_shops(goods: Goods) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    shops = sorted(goods.xgj_publish_shops, key=lambda item: item.sort_order)
    for shop in shops:
        images = [img.image_url for img in sorted(shop.images, key=lambda item: item.sort_order)]
        if not images and goods.logo_url:
            images = [goods.logo_url]
        if not images:
            raise HTTPException(status_code=422, detail="闲管家发布店铺至少需要1张图片")
        item = {
            "user_name": shop.user_name,
            "province": shop.province,
            "city": shop.city,
            "district": shop.district,
            "title": shop.title,
            "content": shop.content,
            "images": images,
        }
        if shop.white_image_url:
            item["white_images"] = shop.white_image_url
        if shop.service_support:
            item["service_support"] = shop.service_support
        normalized.append(item)
    return normalized


def _build_xgj_product_payload(goods: Goods) -> dict[str, Any]:
    if goods.xgj_profile is None:
        raise HTTPException(status_code=422, detail="缺少闲管家商品配置")
    if not goods.xgj_publish_shops:
        raise HTTPException(status_code=422, detail="缺少闲管家发布店铺配置")

    enabled_specs = [spec for spec in goods.specs if spec.enabled]
    price = goods.price_cents
    stock = goods.stock
    if goods.multi_spec and enabled_specs:
        price = min(spec.price_cents for spec in enabled_specs)
        stock = sum(spec.stock for spec in enabled_specs)

    profile = goods.xgj_profile
    payload: dict[str, Any] = {
        "item_biz_type": profile.item_biz_type,
        "sp_biz_type": profile.sp_biz_type,
        "channel_cat_id": profile.channel_cat_id,
        "price": max(1, int(price)),
        "original_price": max(0, int(profile.original_price_cents)),
        "express_fee": max(0, int(profile.express_fee_cents)),
        "stock": max(1, int(stock)),
        "outer_id": goods.goods_no,
        "stuff_status": profile.stuff_status,
        "publish_shop": _build_xgj_publish_shops(goods),
    }
    if profile.category_id is not None:
        payload["category_id"] = profile.category_id
    if profile.notify_url:
        payload["notify_url"] = profile.notify_url
    if profile.flash_sale_type is not None:
        payload["flash_sale_type"] = profile.flash_sale_type
    if profile.is_tax_included:
        payload["is_tax_included"] = profile.is_tax_included
    if goods.xgj_properties:
        payload["channel_pv"] = [
            {
                "property_id": item.property_id,
                "property_name": item.property_name,
                "value_id": item.value_id,
                "value_name": item.value_name,
            }
            for item in sorted(goods.xgj_properties, key=lambda prop: prop.sort_order)
        ]

    if goods.multi_spec and enabled_specs:
        payload["sku_items"] = [
            {
                "price": max(1, int(spec.price_cents)),
                "stock": max(0, int(spec.stock)),
                "sku_text": _build_xgj_sku_text(goods, spec),
                "outer_id": spec.xgj_outer_id or str(spec.id),
            }
            for spec in enabled_specs
        ]

    if goods.xgj_goods_id:
        try:
            payload["product_id"] = int(goods.xgj_goods_id)
        except (TypeError, ValueError):
            payload["product_id"] = goods.xgj_goods_id
    return payload


async def _sync_goods_to_xgj(db: DbSession, goods_id: uuid.UUID) -> Goods:
    goods = await _load_goods_full(db, goods_id)
    if not settings.XGJ_ERP_APP_KEY or not settings.XGJ_ERP_APP_SECRET:
        return goods

    payload = _build_xgj_product_payload(goods)

    try:
        async with _get_erp_client() as client:
            if goods.xgj_goods_id:
                result = await client.edit_product(payload)
            else:
                result = await client.create_product(payload)
                product_id = result.get("product_id") if isinstance(result, dict) else None
                if product_id:
                    goods.xgj_goods_id = str(product_id)
            if goods.xgj_profile and isinstance(result, dict):
                if result.get("product_status") is not None:
                    goods.xgj_profile.product_status = result.get("product_status")
    except XGJApiError as exc:
        raise HTTPException(status_code=502, detail=f"同步闲管家失败: {exc.msg}")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"同步闲管家失败: {exc}")

    return goods


async def _apply_goods_xgj_data(db: DbSession, goods: Goods, body: GoodsCreate | GoodsUpdate, *, partial: bool) -> None:
    if getattr(body, "xgj_profile", None) is not None or not partial:
        _apply_xgj_profile(goods, body.xgj_profile, partial=partial)
    if not partial or body.xgj_properties is not None:
        _replace_xgj_properties(goods, body.xgj_properties or [])
    if not partial or body.xgj_publish_shops is not None:
        await _replace_xgj_publish_shops(db, goods, body.xgj_publish_shops or [])


def _raise_goods_read_only() -> None:
    raise HTTPException(status_code=405, detail="商品为云端只读，请使用同步按钮从闲管家拉取数据")


@router.post("/goods/sync")
async def sync_goods_from_cloud(db: DbSession) -> ApiResponse:
    result: XgjGoodsSyncOut = await _sync_xgj_goods_from_cloud(db)
    return ApiResponse(data=result.model_dump())


@router.post("/goods")
async def create_goods(body: GoodsCreate, db: DbSession) -> ApiResponse:
    _raise_goods_read_only()


@router.get("/goods/{goods_id}")
async def get_goods(goods_id: uuid.UUID, db: DbSession) -> ApiResponse:
    goods = await _load_goods_full(db, goods_id)
    return ApiResponse(data=GoodsOut.model_validate(goods).model_dump(mode="json"))


@router.patch("/goods/{goods_id}")
async def update_goods(goods_id: uuid.UUID, body: GoodsUpdate, db: DbSession) -> ApiResponse:
    _raise_goods_read_only()


@router.delete("/goods/{goods_id}")
async def delete_goods(goods_id: uuid.UUID, db: DbSession) -> ApiResponse:
    _raise_goods_read_only()


@router.post("/goods/{goods_id}/logo")
async def upload_goods_logo(
    goods_id: uuid.UUID,
    db: DbSession,
    file: UploadFile = File(..., description="商品图片"),
) -> ApiResponse:
    _raise_goods_read_only()


@router.post("/uploads/image")
async def upload_admin_image(
    file: UploadFile = File(..., description="后台上传图片"),
) -> ApiResponse:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="文件为空")

    from app.infra.storage import StorageService

    try:
        storage = StorageService()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"存储服务不可用: {exc}")

    source_name = file.filename or "image"
    suffix = Path(source_name).suffix or ".png"
    safe_stem = Path(source_name).stem.replace(" ", "_") or "image"
    storage_key = f"admin/uploads/{uuid.uuid4().hex}-{safe_stem}{suffix}"
    storage.put_bytes(storage_key, data, file.content_type or "image/png")
    return ApiResponse(data={"url": storage.public_url(storage_key)})


# ── 商品规格 ──────────────────────────────────────────────────────────

@router.post("/goods/{goods_id}/specs")
async def create_goods_spec(goods_id: uuid.UUID, body: GoodsSpecCreate, db: DbSession) -> ApiResponse:
    _raise_goods_read_only()


@router.patch("/goods/{goods_id}/specs/{spec_id}")
async def update_goods_spec(
    goods_id: uuid.UUID,
    spec_id: uuid.UUID,
    body: GoodsSpecUpdate,
    db: DbSession,
) -> ApiResponse:
    _raise_goods_read_only()


@router.delete("/goods/{goods_id}/specs/{spec_id}")
async def delete_goods_spec(goods_id: uuid.UUID, spec_id: uuid.UUID, db: DbSession) -> ApiResponse:
    _raise_goods_read_only()


# ── 规格-SKU 发货时机绑定 ─────────────────────────────────────────────

@router.put("/goods/{goods_id}/specs/{spec_id}/bindings")
async def set_spec_bindings(
    goods_id: uuid.UUID,
    spec_id: uuid.UUID,
    body: list[SpecSkuBindingIn],
    db: DbSession,
) -> ApiResponse:
    _raise_goods_read_only()


# ── 规格配置（批量设置维度 + 变体）────────────────────────────────────

@router.put("/goods/{goods_id}/spec-config")
async def set_spec_config(
    goods_id: uuid.UUID,
    body: SpecConfigIn,
    db: DbSession,
) -> ApiResponse:
    _raise_goods_read_only()


# ── 闲管家虚拟货源订单 ───────────────────────────────────────────────

@router.get("/xgj-orders")
async def list_xgj_orders(
    db: DbSession,
    status: int | None = Query(None),
    goods_no: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ApiResponse:
    stmt = select(XgjOrder).order_by(XgjOrder.created_at.desc())
    if status is not None:
        stmt = stmt.where(XgjOrder.status == status)
    if goods_no:
        stmt = stmt.where(XgjOrder.goods_no == goods_no)
    result = await db.execute(stmt.limit(limit).offset(offset))
    items = result.scalars().all()
    count_stmt = select(func.count()).select_from(XgjOrder)
    if status is not None:
        count_stmt = count_stmt.where(XgjOrder.status == status)
    if goods_no:
        count_stmt = count_stmt.where(XgjOrder.goods_no == goods_no)
    total = (await db.execute(count_stmt)).scalar_one()
    return ApiResponse(data={
        "total": total,
        "items": [XgjOrderOut.model_validate(o).model_dump(mode="json") for o in items],
    })


@router.get("/xgj-orders/{order_id}")
async def get_xgj_order(order_id: uuid.UUID, db: DbSession) -> ApiResponse:
    order = await db.get(XgjOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return ApiResponse(data=XgjOrderOut.model_validate(order).model_dump(mode="json"))


# ── 商品变更通知辅助 ──────────────────────────────────────────────────

async def _notify_goods_change(db, goods: Goods) -> None:
    """向所有订阅了该商品的 notify_url 推送变更通知。"""
    try:
        from app.core.database import async_session_factory
        async with async_session_factory() as session:
            result = await session.execute(
                select(GoodsSubscription).where(GoodsSubscription.goods_id == goods.id)
            )
            subs = result.scalars().all()
            if not subs:
                return
            client = _get_virtual_client()
            for sub in subs:
                try:
                    await client.notify_product_change(
                        notify_url=sub.notify_url,
                        goods_no=goods.goods_no,
                    )
                except Exception as exc:
                    logging.getLogger(__name__).warning(
                        "商品变更通知失败 goods_no=%s url=%s: %s",
                        goods.goods_no, sub.notify_url, exc,
                    )
    except Exception as exc:
        logging.getLogger(__name__).warning("商品变更通知任务异常: %s", exc)


def _get_virtual_client():
    from app.infra.xgj.virtual_client import XGJVirtualClient
    return XGJVirtualClient(
        app_id=settings.XGJ_VIRTUAL_APP_KEY,
        app_secret=settings.XGJ_VIRTUAL_APP_SECRET,
        mch_id=settings.XGJ_VIRTUAL_MCH_ID,
        mch_secret=settings.XGJ_VIRTUAL_MCH_SECRET,
    )

