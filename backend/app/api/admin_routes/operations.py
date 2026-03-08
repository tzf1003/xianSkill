from __future__ import annotations

import asyncio
import hashlib
import uuid

from fastapi import BackgroundTasks, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import func, select

from app.api.schemas import ApiResponse, DeliveryRecordOut, JobOut, OrderCreate, OrderOut, TokenCreate, TokenOut, WebhookCreate, WebhookOut
from app.core.config import settings
from app.core.deps import DbSession
from app.domain.models import Asset, DeliveryRecord, Job, JobStatus, Order, SKU, Skill, Token, TokenStatus, Webhook
from app.services import job_service, token_service

from .common import router


@router.get("/orders")
async def list_orders(
    db: DbSession,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ApiResponse:
    result = await db.execute(select(Order).order_by(Order.created_at.desc()).limit(limit).offset(offset))
    orders = result.scalars().all()
    total = (await db.execute(select(func.count()).select_from(Order))).scalar_one()
    return ApiResponse(data={
        "total": total,
        "items": [OrderOut.model_validate(order).model_dump(mode="json") for order in orders],
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
    token_result = await db.execute(select(Token).where(Token.order_id == order_id))
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
    items = [
        TokenOut(
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
        ).model_dump(mode="json")
        for token in tokens
    ]
    return ApiResponse(data={"total": total, "items": items})


@router.delete("/tokens/{token_id}")
async def revoke_token(token_id: uuid.UUID, db: DbSession) -> ApiResponse:
    token = await db.get(Token, token_id)
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    token.status = TokenStatus.revoked
    await db.commit()
    return ApiResponse(data={"id": str(token_id), "status": "revoked"})


@router.post("/tokens")
async def create_token_direct(body: TokenCreate, db: DbSession) -> ApiResponse:
    sku = await db.get(SKU, body.sku_id)
    if not sku:
        raise HTTPException(status_code=404, detail="SKU not found")

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


@router.get("/jobs")
async def list_jobs(
    db: DbSession,
    status: str | None = Query(None),
    skill_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ApiResponse:
    from app.api.public import _job_out
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

    try:
        storage = StorageService()
    except Exception:
        storage = None
    return ApiResponse(data={
        "total": total,
        "items": [_job_out(job, storage).model_dump(mode="json") for job in jobs],
    })


@router.get("/jobs/{job_id}")
async def get_job(job_id: uuid.UUID, db: DbSession) -> ApiResponse:
    from app.api.public import _job_out
    from app.infra.storage import StorageService

    job = await job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        storage = StorageService()
    except Exception:
        storage = None
    return ApiResponse(data=_job_out(job, storage).model_dump(mode="json"))


@router.post("/jobs/{job_id}/retry")
async def retry_job(job_id: uuid.UUID, db: DbSession, background_tasks: BackgroundTasks) -> ApiResponse:
    from app.tasks.execute_job import run_job

    job = await job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status == JobStatus.succeeded:
        raise HTTPException(status_code=409, detail="Job already succeeded")

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
async def finalize_job(job_id: uuid.UUID, db: DbSession, success: bool = True, error: str | None = None) -> ApiResponse:
    job = await job_service.finalize_job(db, job_id, success=success, error=error)
    await db.commit()
    await db.refresh(job)
    return ApiResponse(data=JobOut.model_validate(job).model_dump(mode="json"))


@router.post("/jobs/{job_id}/human-deliver")
async def human_deliver(
    job_id: uuid.UUID,
    db: DbSession,
    operator: str = Form(..., description="操作人姓名"),
    notes: str | None = Form(None, description="备注"),
    file: UploadFile = File(..., description="交付产物文件"),
) -> ApiResponse:
    from app.api.public import _job_out
    from app.infra.storage import StorageService

    job = await job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in (JobStatus.queued, JobStatus.running):
        raise HTTPException(status_code=409, detail=f"Job already in terminal state: {job.status.value}")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    output_hash = hashlib.sha256(data).hexdigest()

    try:
        storage = StorageService()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Storage unavailable: {exc}")

    safe_name = (file.filename or "delivery").replace(" ", "_")
    storage_key = f"deliveries/{job_id}/{safe_name}"
    storage.put_bytes(storage_key, data, file.content_type or "application/octet-stream")

    db.add(
        Asset(
            job_id=job_id,
            filename=safe_name,
            storage_key=storage_key,
            content_type=file.content_type,
            size_bytes=len(data),
            hash=output_hash,
        )
    )
    db.add(DeliveryRecord(job_id=job_id, operator=operator, notes=notes, output_hash=output_hash))

    await db.flush()
    job = await job_service.finalize_job(db, job_id, success=True, result={"delivered_by": operator})
    await db.commit()
    await db.refresh(job)

    return ApiResponse(data=_job_out(job, storage).model_dump(mode="json"))


@router.get("/jobs/{job_id}/delivery-record")
async def get_delivery_record(job_id: uuid.UUID, db: DbSession) -> ApiResponse:
    result = await db.execute(select(DeliveryRecord).where(DeliveryRecord.job_id == job_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Delivery record not found")
    return ApiResponse(data=DeliveryRecordOut.model_validate(record).model_dump(mode="json"))


@router.get("/webhooks")
async def list_webhooks(db: DbSession) -> ApiResponse:
    result = await db.execute(select(Webhook).order_by(Webhook.created_at.desc()))
    webhooks = result.scalars().all()
    return ApiResponse(data={"items": [WebhookOut.model_validate(webhook).model_dump(mode="json") for webhook in webhooks]})


@router.post("/webhooks")
async def create_webhook(body: WebhookCreate, db: DbSession) -> ApiResponse:
    webhook = Webhook(url=body.url, secret=body.secret, events=body.events, description=body.description)
    db.add(webhook)
    await db.commit()
    await db.refresh(webhook)
    return ApiResponse(data=WebhookOut.model_validate(webhook).model_dump(mode="json"))


@router.put("/webhooks/{webhook_id}")
async def update_webhook(webhook_id: uuid.UUID, body: WebhookCreate, db: DbSession) -> ApiResponse:
    webhook = await db.get(Webhook, webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    webhook.url = body.url
    webhook.secret = body.secret
    webhook.events = body.events
    webhook.description = body.description
    await db.commit()
    await db.refresh(webhook)
    return ApiResponse(data=WebhookOut.model_validate(webhook).model_dump(mode="json"))


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: uuid.UUID, db: DbSession) -> ApiResponse:
    webhook = await db.get(Webhook, webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    await db.delete(webhook)
    await db.commit()
    return ApiResponse(data={"id": str(webhook_id), "deleted": True})


@router.post("/webhooks/{webhook_id}/disable")
async def disable_webhook(webhook_id: uuid.UUID, db: DbSession) -> ApiResponse:
    webhook = await db.get(Webhook, webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    webhook.enabled = False
    await db.commit()
    return ApiResponse(data={"id": str(webhook_id), "enabled": False})