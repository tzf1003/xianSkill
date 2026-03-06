"""Admin API — 完整后台管理（AGENT.md §9：/v1/admin/...）。"""

from __future__ import annotations

import asyncio
import hashlib
import uuid

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import func, select

from app.api.schemas import (
    ApiResponse,
    DeliveryRecordOut,
    JobOut,
    OrderCreate,
    OrderOut,
    SKUCreate,
    SKUOut,
    SKUUpdate,
    SkillCreate,
    SkillOut,
    SkillUpdate,
    StatsOut,
    TokenOut,
    WebhookCreate,
    WebhookOut,
)
from app.core.config import settings
from app.core.deps import DbSession, get_storage
from app.domain.models import (
    Asset,
    DeliveryRecord,
    DeliveryMode,
    Job,
    JobStatus,
    Order,
    SKU,
    Skill,
    SkillType,
    Token,
    TokenStatus,
    Webhook,
)
from app.services import job_service, token_service

router = APIRouter(prefix="/v1/admin", tags=["admin"])


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
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ApiResponse:
    stmt = select(SKU).order_by(SKU.created_at.desc())
    if skill_id:
        stmt = stmt.where(SKU.skill_id == skill_id)
    result = await db.execute(stmt.limit(limit).offset(offset))
    skus = result.scalars().all()
    count_stmt = select(func.count()).select_from(SKU)
    if skill_id:
        count_stmt = count_stmt.where(SKU.skill_id == skill_id)
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
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ApiResponse:
    stmt = select(Token).order_by(Token.created_at.desc())
    if status:
        try:
            stmt = stmt.where(Token.status == TokenStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    result = await db.execute(stmt.limit(limit).offset(offset))
    tokens = result.scalars().all()
    count_stmt = select(func.count()).select_from(Token)
    if status:
        count_stmt = count_stmt.where(Token.status == TokenStatus(status))
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

