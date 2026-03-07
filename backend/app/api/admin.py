"""Admin API — 完整后台管理（AGENT.md §9：/v1/admin/...）。"""

from __future__ import annotations

import asyncio
import hashlib
import uuid

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
    XgjOrder,
)
from app.services import job_service, token_service

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
        options=body.options,
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
    stmt = select(Goods).order_by(Goods.created_at.desc())
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


@router.post("/goods")
async def create_goods(body: GoodsCreate, db: DbSession) -> ApiResponse:
    # 自动生成商品编号：G + 时间戳 + 4位随机
    import time as _t, secrets as _sec
    goods_no = f"G{int(_t.time())}{_sec.token_hex(2).upper()}"
    # 校验规格维度约束
    if body.spec_groups:
        try:
            validate_spec_groups(body.spec_groups)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
    goods = Goods(
        goods_no=goods_no,
        goods_type=body.goods_type,
        goods_name=body.goods_name,
        logo_url=body.logo_url,
        price_cents=body.price_cents,
        stock=body.stock,
        status=body.status,
        multi_spec=body.multi_spec,
        spec_groups=body.spec_groups,
        template=body.template,
        description=body.description,
    )
    db.add(goods)
    await db.flush()

    # 创建规格
    for spec_in in body.specs:
        spec = GoodsSpec(
            goods_id=goods.id,
            spec_name=spec_in.spec_name,
            price_cents=spec_in.price_cents,
            stock=spec_in.stock,
            enabled=spec_in.enabled,
        )
        db.add(spec)
        await db.flush()
        # 创建发货时机绑定
        for binding_in in spec_in.sku_bindings:
            binding = SpecSkuBinding(
                spec_id=spec.id,
                timing=DeliveryTiming(binding_in.timing),
                sku_id=binding_in.sku_id,
            )
            db.add(binding)

    await db.commit()
    await db.refresh(goods)
    return ApiResponse(data=GoodsOut.model_validate(goods).model_dump(mode="json"))


@router.get("/goods/{goods_id}")
async def get_goods(goods_id: uuid.UUID, db: DbSession) -> ApiResponse:
    goods = await db.get(Goods, goods_id)
    if not goods:
        raise HTTPException(status_code=404, detail="商品不存在")
    return ApiResponse(data=GoodsOut.model_validate(goods).model_dump(mode="json"))


@router.patch("/goods/{goods_id}")
async def update_goods(goods_id: uuid.UUID, body: GoodsUpdate, db: DbSession) -> ApiResponse:
    goods = await db.get(Goods, goods_id)
    if not goods:
        raise HTTPException(status_code=404, detail="商品不存在")
    # 校验规格维度约束
    updates = body.model_dump(exclude_unset=True)
    if "spec_groups" in updates and updates["spec_groups"]:
        try:
            validate_spec_groups(updates["spec_groups"])
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
    for field, value in updates.items():
        setattr(goods, field, value)
    await db.commit()
    await db.refresh(goods)

    # 通知订阅方商品变更
    asyncio.create_task(_notify_goods_change(db, goods))

    return ApiResponse(data=GoodsOut.model_validate(goods).model_dump(mode="json"))


@router.delete("/goods/{goods_id}")
async def delete_goods(goods_id: uuid.UUID, db: DbSession) -> ApiResponse:
    goods = await db.get(Goods, goods_id)
    if not goods:
        raise HTTPException(status_code=404, detail="商品不存在")
    await db.delete(goods)
    await db.commit()
    return ApiResponse(data={"deleted": str(goods_id)})


@router.post("/goods/{goods_id}/logo")
async def upload_goods_logo(
    goods_id: uuid.UUID,
    db: DbSession,
    file: UploadFile = File(..., description="商品图片"),
) -> ApiResponse:
    """上传商品 Logo 图片，存储到 MinIO，更新 logo_url。"""
    goods = await db.get(Goods, goods_id)
    if not goods:
        raise HTTPException(status_code=404, detail="商品不存在")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="文件为空")
    from app.infra.storage import StorageService
    try:
        storage = StorageService()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"存储服务不可用: {exc}")
    safe_name = (file.filename or "logo").replace(" ", "_")
    storage_key = f"goods/{goods_id}/{safe_name}"
    storage.put_bytes(storage_key, data, file.content_type or "image/png")
    logo_url = storage.public_url(storage_key)
    goods.logo_url = logo_url
    await db.commit()
    await db.refresh(goods)
    return ApiResponse(data=GoodsOut.model_validate(goods).model_dump(mode="json"))


# ── 商品规格 ──────────────────────────────────────────────────────────

@router.post("/goods/{goods_id}/specs")
async def create_goods_spec(goods_id: uuid.UUID, body: GoodsSpecCreate, db: DbSession) -> ApiResponse:
    goods = await db.get(Goods, goods_id)
    if not goods:
        raise HTTPException(status_code=404, detail="商品不存在")
    spec = GoodsSpec(
        goods_id=goods_id,
        spec_name=body.spec_name,
        price_cents=body.price_cents,
        stock=body.stock,
        enabled=body.enabled,
    )
    db.add(spec)
    await db.flush()
    for binding_in in body.sku_bindings:
        binding = SpecSkuBinding(
            spec_id=spec.id,
            timing=DeliveryTiming(binding_in.timing),
            sku_id=binding_in.sku_id,
        )
        db.add(binding)
    await db.commit()
    await db.refresh(spec)

    asyncio.create_task(_notify_goods_change(db, goods))

    return ApiResponse(data=GoodsSpecOut.model_validate(spec).model_dump(mode="json"))


@router.patch("/goods/{goods_id}/specs/{spec_id}")
async def update_goods_spec(
    goods_id: uuid.UUID,
    spec_id: uuid.UUID,
    body: GoodsSpecUpdate,
    db: DbSession,
) -> ApiResponse:
    spec = await db.get(GoodsSpec, spec_id)
    if not spec or spec.goods_id != goods_id:
        raise HTTPException(status_code=404, detail="规格不存在")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(spec, field, value)
    await db.commit()
    await db.refresh(spec)

    goods = await db.get(Goods, goods_id)
    if goods:
        asyncio.create_task(_notify_goods_change(db, goods))

    return ApiResponse(data=GoodsSpecOut.model_validate(spec).model_dump(mode="json"))


@router.delete("/goods/{goods_id}/specs/{spec_id}")
async def delete_goods_spec(goods_id: uuid.UUID, spec_id: uuid.UUID, db: DbSession) -> ApiResponse:
    spec = await db.get(GoodsSpec, spec_id)
    if not spec or spec.goods_id != goods_id:
        raise HTTPException(status_code=404, detail="规格不存在")
    await db.delete(spec)
    await db.commit()

    goods = await db.get(Goods, goods_id)
    if goods:
        asyncio.create_task(_notify_goods_change(db, goods))

    return ApiResponse(data={"deleted": str(spec_id)})


# ── 规格-SKU 发货时机绑定 ─────────────────────────────────────────────

@router.put("/goods/{goods_id}/specs/{spec_id}/bindings")
async def set_spec_bindings(
    goods_id: uuid.UUID,
    spec_id: uuid.UUID,
    body: list[SpecSkuBindingIn],
    db: DbSession,
) -> ApiResponse:
    """设置/更新规格的发货时机绑定（全量替换）。"""
    spec = await db.get(GoodsSpec, spec_id)
    if not spec or spec.goods_id != goods_id:
        raise HTTPException(status_code=404, detail="规格不存在")
    # 删除旧绑定
    old_bindings = await db.execute(
        select(SpecSkuBinding).where(SpecSkuBinding.spec_id == spec_id)
    )
    for b in old_bindings.scalars().all():
        await db.delete(b)
    # 创建新绑定
    for binding_in in body:
        binding = SpecSkuBinding(
            spec_id=spec_id,
            timing=DeliveryTiming(binding_in.timing),
            sku_id=binding_in.sku_id,
        )
        db.add(binding)
    await db.commit()
    await db.refresh(spec)
    return ApiResponse(data=GoodsSpecOut.model_validate(spec).model_dump(mode="json"))


# ── 规格配置（批量设置维度 + 变体）────────────────────────────────────

@router.put("/goods/{goods_id}/spec-config")
async def set_spec_config(
    goods_id: uuid.UUID,
    body: SpecConfigIn,
    db: DbSession,
) -> ApiResponse:
    """整体设置多规格商品的规格维度与组合变体。

    - spec_groups: 最多 2 组规格，单个规格最多 150 个属性值，两组时组合 ≤ 400
    - variants: 对应的 SKU 组合列表，每个有 spec_name / price / stock / bindings
    """
    goods = await db.get(Goods, goods_id)
    if not goods:
        raise HTTPException(status_code=404, detail="商品不存在")

    # 校验规格维度约束
    try:
        validate_spec_groups(body.spec_groups)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # 保存规格维度定义
    goods.spec_groups = body.spec_groups
    goods.multi_spec = True

    # 删除当前所有 GoodsSpec（全量替换）
    old_specs = await db.execute(
        select(GoodsSpec).where(GoodsSpec.goods_id == goods_id)
    )
    for old in old_specs.scalars().all():
        await db.delete(old)
    await db.flush()

    # 创建新的变体
    for v in body.variants:
        spec = GoodsSpec(
            goods_id=goods_id,
            spec_name=v.spec_name,
            price_cents=v.price_cents,
            stock=v.stock,
            enabled=v.enabled,
        )
        db.add(spec)
        await db.flush()
        for binding_in in v.sku_bindings:
            db.add(SpecSkuBinding(
                spec_id=spec.id,
                timing=DeliveryTiming(binding_in.timing),
                sku_id=binding_in.sku_id,
            ))

    await db.commit()

    asyncio.create_task(_notify_goods_change(db, goods))

    # 重新查询并预加载所有关系，避免懒加载在序列化时触发 MissingGreenlet
    refreshed = await db.execute(
        select(Goods)
        .where(Goods.id == goods_id)
        .options(
            selectinload(Goods.specs).selectinload(GoodsSpec.sku_bindings)
        )
    )
    goods = refreshed.scalar_one()

    return ApiResponse(data=GoodsOut.model_validate(goods).model_dump(mode="json"))


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

