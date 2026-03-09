"""Public API — 面向用户 token 使用（AGENT.md §9：/v1/public/...）。"""

from __future__ import annotations

import hashlib
import io
import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from PIL import Image
from sqlalchemy import select

from app.api.schemas import ApiResponse, AssetOut, JobOut, JobSubmit, LatestJobBrief, TokenInfo, SkillOut, ProjectOut, UploadOut
from app.core.config import settings
from app.core.deps import DbSession, get_storage
from app.domain.models import Job, JobStatus, Project, PushChannel, Skill, SKU, XgjOrder
from app.infra.queue import get_queue
from app.infra.storage import StorageService
from app.infra.xgj.virtual_client import XGJVirtualClient
from app.services import job_service, token_service
from app.services.push_service import HUMAN_PUSH_TITLE, build_human_order_message, extract_xgj_notify_url, send_push_message
from app.tasks.execute_job import execute_job

router = APIRouter(prefix="/v1/public", tags=["public"])
logger = logging.getLogger(__name__)

_MAX_UPLOAD_BYTES = 20 * 1024 * 1024   # 20 MB 硬上限
_COMPRESS_THRESHOLD = 5 * 1024 * 1024   # 超过 5 MB 尝试压缩


async def _find_xgj_order_for_token(db: DbSession, token_id) -> XgjOrder | None:
    stmt = select(XgjOrder).where(XgjOrder.local_token_id == token_id).order_by(XgjOrder.created_at.desc())
    return (await db.execute(stmt)).scalars().first()


async def _notify_human_job_created(db: DbSession, *, job: Job, token, sku: SKU) -> None:
    xgj_order = await _find_xgj_order_for_token(db, token.id)
    if xgj_order is not None:
        delivery_info = xgj_order.delivery_info if isinstance(xgj_order.delivery_info, dict) else {}
        if delivery_info.get("human_erp_notified"):
            return

    buyer_info = xgj_order.buyer_info if xgj_order and isinstance(xgj_order.buyer_info, dict) else None
    source_order_no = None
    if xgj_order is not None:
        source_order_no = xgj_order.source_order_no or xgj_order.order_no or xgj_order.out_order_no

    if sku.push_channel_id:
        channel = await db.get(PushChannel, sku.push_channel_id)
        if channel and channel.enabled:
            body = build_human_order_message(
                sku=sku,
                job_id=str(job.id),
                token_value=token.token,
                local_order_id=str(token.order_id),
                source_order_no=source_order_no,
                buyer_info=buyer_info,
                inputs=job.inputs,
            )
            try:
                await send_push_message(channel, title=HUMAN_PUSH_TITLE, body=body)
            except Exception as exc:
                logger.warning("human push failed: job=%s channel=%s error=%s", job.id, channel.id, exc)

    notify_url = extract_xgj_notify_url(xgj_order)
    if not notify_url or xgj_order is None:
        return

    try:
        from app.api.xgj_virtual import _build_xgj_order_payload

        xgj_order.status = 0
        await db.commit()
        payload = _build_xgj_order_payload(
            xgj_order,
            goods_name=str((xgj_order.delivery_info or {}).get("goods_name") or sku.name),
        )
        async with XGJVirtualClient(
            app_id=settings.XGJ_VIRTUAL_APP_KEY,
            app_secret=settings.XGJ_VIRTUAL_APP_SECRET,
            mch_id=settings.XGJ_VIRTUAL_MCH_ID,
            mch_secret=settings.XGJ_VIRTUAL_MCH_SECRET,
        ) as client:
            await client.notify_order_result(notify_url, payload)
    except Exception as exc:
        logger.warning("xgj human pending notify failed: job=%s order=%s error=%s", job.id, getattr(xgj_order, "id", None), exc)


def _compress_image(data: bytes) -> tuple[bytes, str]:
    """尝试无损/近无损压缩图片。返回 (压缩后字节, content_type)。

    策略：
    - PNG → 用 Pillow 重新保存（optimize），仍为 PNG
    - JPEG/MPO 等 → 以 quality=90 重新编码 JPEG（近无损，体积大幅下降）
    - WebP → quality=90 有损重编码
    - 其他/失败 → 返回原始数据
    """
    try:
        img = Image.open(io.BytesIO(data))
        fmt = (img.format or "").upper()
    except Exception:
        return data, "application/octet-stream"

    buf = io.BytesIO()
    if fmt == "PNG":
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue(), "image/png"
    elif fmt in ("JPEG", "MPO", ""):
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
        img.save(buf, format="JPEG", quality=90, optimize=True)
        return buf.getvalue(), "image/jpeg"
    elif fmt == "WEBP":
        img.save(buf, format="WEBP", quality=90)
        return buf.getvalue(), "image/webp"
    else:
        # GIF 等格式不压缩
        return data, f"image/{fmt.lower()}"


@router.get("/token/{token_value}")
async def get_token_info(token_value: str, db: DbSession) -> ApiResponse:
    """查询 token 绑定的 skill 信息、delivery_mode、剩余次数、状态、最新 Job。"""
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

    # 查询最新 Job（按创建时间倒序）
    latest_job = None
    if token.jobs:
        job = sorted(token.jobs, key=lambda j: j.created_at, reverse=True)[0]
        try:
            storage = StorageService()
        except Exception:
            storage = None
        assets_out = [
            AssetOut(
                id=a.id,
                filename=a.filename,
                storage_key=a.storage_key,
                content_type=a.content_type,
                size_bytes=a.size_bytes,
                download_url=(
                    storage.presigned_get_url(a.storage_key)
                    if storage and a.storage_key
                    else ""
                ),
            )
            for a in job.assets
        ]
        latest_job = LatestJobBrief(
            id=job.id,
            status=job.status.value if hasattr(job.status, "value") else str(job.status),
            created_at=job.created_at,
            finished_at=job.finished_at,
            assets=assets_out,
        )

    # 查询项目（从 SKU 的 project_id 确定）
    project_out = None
    if sku and sku.project_id:
        proj_stmt = select(Project).where(Project.id == sku.project_id)
        project = (await db.execute(proj_stmt)).scalar_one_or_none()
        if project:
            project_out = ProjectOut.model_validate(project)

    info = TokenInfo(
        token=token.token,
        skill=SkillOut.model_validate(skill),
        sku_name=sku.name if sku else "",
        delivery_mode=sku.delivery_mode.value if sku else "auto",
        human_sla_hours=sku.human_sla_hours if sku else None,
        total_uses=token.total_uses,
        remaining=token.remaining,
        status=token.status.value,
        expires_at=token.expires_at,
        latest_job=latest_job,
        project=project_out,
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
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"文件大小 {len(data) / 1024 / 1024:.1f}MB 超过上限 20MB",
        )

    content_type = file.content_type or "application/octet-stream"
    if len(data) > _COMPRESS_THRESHOLD:
        data, content_type = _compress_image(data)

    file_uuid = uuid.uuid4()
    safe_name = (file.filename or "upload").replace(" ", "_")
    object_key = f"uploads/{file_uuid}/{safe_name}"
    input_hash = hashlib.sha256(data).hexdigest()

    storage.put_bytes(object_key, data, content_type)

    return ApiResponse(data=UploadOut(object_key=object_key, input_hash=input_hash).model_dump())


@router.post("/job")
async def submit_job(
    body: JobSubmit,
    db: DbSession,
) -> ApiResponse:
    """提交 Job：带 token + inputs + 可选 idempotency_key。

    human delivery_mode 的 Job 不进入 worker 队列，由管理员手动交付。
    """
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

    # 仅 auto 模式的新建排队 Job 才触发执行
    if job.status == JobStatus.queued:
        sku_stmt = select(SKU).where(SKU.id == token.sku_id)
        sku = (await db.execute(sku_stmt)).scalar_one_or_none()
        is_human = sku and sku.delivery_mode.value == "human"
        if is_human:
            await _notify_human_job_created(db, job=job, token=token, sku=sku)
        else:
            get_queue().enqueue(execute_job, str(job.id))

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


@router.get("/jobs")
async def list_jobs_by_token(
    token_value: str,
    db: DbSession,
    storage: StorageService = Depends(get_storage),
) -> ApiResponse:
    """查询该 token 下所有 Job（按创建时间倒序），含 assets 预签名 URL。"""
    from app.domain.models import Token as TokenModel
    token_row = (await db.execute(select(TokenModel).where(TokenModel.token == token_value))).scalar_one_or_none()
    if not token_row:
        raise HTTPException(status_code=404, detail="Token not found")
    jobs = sorted(token_row.jobs, key=lambda j: j.created_at, reverse=True)
    try:
        storage_svc = StorageService()
    except Exception:
        storage_svc = None
    return ApiResponse(data=[_job_out(j, storage_svc).model_dump(mode="json") for j in jobs])


@router.get("/projects")
async def list_projects(db: DbSession) -> ApiResponse:
    """列出所有已启用的项目（公开，无需 token）。"""
    stmt = select(Project).where(Project.enabled.is_(True)).order_by(Project.created_at)
    rows = (await db.execute(stmt)).scalars().all()
    return ApiResponse(data=[ProjectOut.model_validate(r).model_dump(mode="json") for r in rows])


@router.get("/projects/{slug}")
async def get_project(slug: str, db: DbSession) -> ApiResponse:
    """根据 slug 获取项目详情（公开，无需 token）。"""
    stmt = select(Project).where(Project.slug == slug, Project.enabled.is_(True))
    project = (await db.execute(stmt)).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ApiResponse(data=ProjectOut.model_validate(project).model_dump(mode="json"))


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

