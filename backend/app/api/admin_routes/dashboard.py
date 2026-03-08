from __future__ import annotations

from sqlalchemy import func, select

from app.api.schemas import ApiResponse, StatsOut
from app.core.deps import DbSession
from app.domain.models import Job, JobStatus, Order, SKU, Skill, Token

from .common import router


@router.get("/stats")
async def get_stats(db: DbSession) -> ApiResponse:
    async def count(model):
        result = await db.execute(select(func.count()).select_from(model))
        return result.scalar_one()

    async def count_jobs_by_status(status: JobStatus):
        result = await db.execute(select(func.count()).select_from(Job).where(Job.status == status))
        return result.scalar_one()

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