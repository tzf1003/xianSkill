"""Job 服务 — 提交 / 查询 / 状态机流转。

Job 状态机（AGENT.md §9）：queued → running → succeeded | failed | canceled
submit_job 支持 idempotency_key 避免重复扣次与重复 Job。
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Job, JobStatus, Token
from app.services import token_service


async def submit_job(
    session: AsyncSession,
    *,
    token: Token,
    idempotency_key: str | None = None,
    inputs: dict | None = None,
) -> Job:
    """提交一个 Job。

    - scope 校验已在路由层完成
    - 幂等：若 idempotency_key 已存在，直接返回已有 Job（不重复扣次）
    - reserve 一次
    """
    # 幂等检查
    if idempotency_key:
        stmt = select(Job).where(
            Job.token_id == token.id,
            Job.idempotency_key == idempotency_key,
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing

    # 校验 token 可用性
    token_service.validate_token_usable(token)

    # reserve（冻结一次）
    token_service.reserve(token)

    job = Job(
        token_id=token.id,
        skill_id=token.skill_id,
        idempotency_key=idempotency_key,
        inputs=inputs,
        status=JobStatus.queued,
    )
    session.add(job)
    return job


async def get_job(session: AsyncSession, job_id: uuid.UUID) -> Job | None:
    stmt = select(Job).where(Job.id == job_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def finalize_job(
    session: AsyncSession,
    job_id: uuid.UUID,
    *,
    success: bool,
    result: dict | None = None,
    error: str | None = None,
) -> Job:
    """手动 finalize（M1 测试用）：标记 Job 完成并执行 token 计次 finalize。"""
    stmt = select(Job).where(Job.id == job_id)
    res = await session.execute(stmt)
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in (JobStatus.queued, JobStatus.running):
        raise HTTPException(status_code=409, detail=f"Job already in terminal state: {job.status.value}")

    # 加载 token
    token_stmt = select(Token).where(Token.id == job.token_id)
    token_res = await session.execute(token_stmt)
    token = token_res.scalar_one_or_none()
    if not token:
        raise HTTPException(status_code=500, detail="Token not found for job")

    if success:
        job.status = JobStatus.succeeded
        job.result = result
        token_service.finalize_success(token)
    else:
        job.status = JobStatus.failed
        job.error = error or "manually failed"
        token_service.finalize_failure(token)

    from datetime import datetime, timezone
    job.finished_at = datetime.now(timezone.utc)
    return job
