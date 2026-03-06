"""RQ 任务：执行 Job，自动 finalize。

RQ 运行同步函数，通过 asyncio.run() 桥接 async ORM。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select

from app.core.config import settings
from app.domain.models import Asset, Job, JobStatus, Skill, Token
from app.infra.storage import StorageService
from app.runners.prompt_runner import PromptRunner

logger = logging.getLogger(__name__)


def execute_job(job_id_str: str) -> None:
    """RQ task 入口（同步）。"""
    asyncio.run(_run(job_id_str))


async def _run(job_id_str: str) -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    storage = StorageService()

    job_id = uuid.UUID(job_id_str)

    async with factory() as session:
        job = await _load_job(session, job_id)
        if not job:
            logger.error("Job not found: %s", job_id_str)
            return

        skill_row = (await session.execute(select(Skill).where(Skill.id == job.skill_id))).scalar_one()
        token_row = (await session.execute(select(Token).where(Token.id == job.token_id))).scalar_one()

        # 标记运行中
        job.status = JobStatus.running
        job.started_at = datetime.now(timezone.utc)
        await session.commit()

        try:
            runner = PromptRunner()
            run_result = runner.run(
                job_id=str(job.id),
                skill={
                    "prompt_template": skill_row.prompt_template or "Restore this image.",
                    "runner_config": skill_row.runner_config or {},
                },
                inputs=job.inputs or {},
                storage=storage,
            )

            # 持久化 assets
            for asset_data in run_result.assets:
                session.add(
                    Asset(
                        job_id=job.id,
                        filename=asset_data["filename"],
                        storage_key=asset_data["storage_key"],
                        content_type=asset_data.get("content_type"),
                        size_bytes=asset_data.get("size_bytes"),
                        hash=asset_data.get("hash"),
                    )
                )

            output_hash = hashlib.sha256(
                json.dumps(run_result.assets, sort_keys=True).encode()
            ).hexdigest()

            job.status = JobStatus.succeeded
            job.result = {"assets": run_result.assets, "metadata": run_result.metadata}
            job.log_text = run_result.logs
            job.output_hash = output_hash
            job.finished_at = datetime.now(timezone.utc)

            # finalize token（确认扣次数）
            token_row.used_count += 1
            token_row.reserved_count = max(0, token_row.reserved_count - 1)

            logger.info("Job %s succeeded", job_id_str)

        except Exception as exc:
            logger.exception("Job %s failed: %s", job_id_str, exc)
            job.status = JobStatus.failed
            job.error = str(exc)
            job.log_text = f"ERROR: {exc}"
            job.finished_at = datetime.now(timezone.utc)

            # 归还预占
            token_row.reserved_count = max(0, token_row.reserved_count - 1)

        await session.commit()

    await engine.dispose()


async def _load_job(session: AsyncSession, job_id: uuid.UUID) -> Job | None:
    result = await session.execute(select(Job).where(Job.id == job_id))
    return result.scalar_one_or_none()
