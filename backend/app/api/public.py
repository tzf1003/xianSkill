"""Public API — 面向用户 token 使用（AGENT.md §9：/v1/public/...）。"""

from __future__ import annotations

import hashlib
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.schemas import ApiResponse, AssetOut, JobOut, JobSubmit, TokenInfo, SkillOut, UploadOut
from app.core.deps import DbSession, get_queue, get_storage
from app.domain.models import JobStatus, Skill, SKU
from app.infra.storage import StorageService
from app.services import job_service, token_service
from app.tasks.execute_job import execute_job

from sqlalchemy import select

router = APIRouter(prefix="/v1/public", tags=["public"])


@router.get("/token/{token_value}")
async def get_token_info(token_value: str, db: DbSession) -> ApiResponse:
    """查询 token 绑定的 skill 信息、剩余次数、状态、过期时间。"""
    token = await token_service.get_token_by_value(db, token_value)
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    stmt = select(Skill).where(Skill.id == token.skill_id)
    result = await db.execute(stmt)
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=500, detail="Skill not found for token")

    sku_stmt = select(SKU).where(SKU.id == token.sku_id)
    sku = (await db.execute(sku_stmt)).scalar_one_or_none()

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


@router.post("/upload")
async def upload_file(
    db: DbSession,
    storage: StorageService = Depends(get_storage),
    token: str = Form(...),
    file: UploadFile = File(...),
) -> ApiResponse:
    """上传图像到 MinIO，返回 object_key 用于后续提交 Job。"""
    token_obj = await token_service.get_token_by_value(db, token)
    if not token_obj:
        raise HTTPException(status_code=404, detail="Token not found")
    token_service.validate_scope(token_obj)

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    file_uuid = uuid.uuid4()
    safe_name = (file.filename or "upload").replace(" ", "_")
    object_key = f"uploads/{file_uuid}/{safe_name}"
    input_hash = hashlib.sha256(data).hexdigest()

    storage.put_bytes(object_key, data, file.content_type or "application/octet-stream")

    return ApiResponse(data=UploadOut(object_key=object_key, input_hash=input_hash).model_dump())


@router.post("/job")
async def submit_job(
    body: JobSubmit,
    db: DbSession,
    queue=Depends(get_queue),
) -> ApiResponse:
    """提交 Job：带 token + inputs + 可选 idempotency_key。"""
    token = await token_service.get_token_by_value(db, body.token)
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    token_service.validate_scope(token)

    job = await job_service.submit_job(
        db,
        token=token,
        idempotency_key=body.idempotency_key,
        inputs=body.inputs,
    )
    await db.commit()
    await db.refresh(job)

    # 仅对新创建的排队 Job 入队（幂等重试不重复入队）
    if job.status == JobStatus.queued:
        queue.enqueue(execute_job, str(job.id))

    return ApiResponse(data=_job_out(job).model_dump(mode="json"))


@router.get("/job/{job_id}")
async def get_job(
    job_id: uuid.UUID,
    db: DbSession,
    storage: StorageService = Depends(get_storage),
) -> ApiResponse:
    """查询 Job 状态，成功时 assets 包含预签名下载 URL。"""
    job = await job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    out = _job_out(job, storage)
    return ApiResponse(data=out.model_dump(mode="json"))


# ── 内部辅助 ─────────────────────────────────────────────────────────

def _job_out(job, storage: StorageService | None = None) -> JobOut:
    assets = []
    for a in job.assets:
        download_url = ""
        if storage and a.storage_key:
            try:
                download_url = storage.presigned_get_url(a.storage_key)
            except Exception:
                pass
        assets.append(
            AssetOut(
                id=a.id,
                filename=a.filename,
                storage_key=a.storage_key,
                content_type=a.content_type,
                size_bytes=a.size_bytes,
                download_url=download_url,
            )
        )

    return JobOut(
        id=job.id,
        skill_id=job.skill_id,
        status=job.status.value if hasattr(job.status, "value") else str(job.status),
        inputs=job.inputs,
        result=job.result,
        error=job.error,
        log_text=job.log_text,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        assets=assets,
    )

