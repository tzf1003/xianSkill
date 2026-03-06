"""RQ 任务：执行 Job，自动 finalize。

RQ 运行同步函数，通过 asyncio.run() 桥接 async ORM。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import sys
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select

from app.core.config import settings
from app.domain.models import Asset, Job, JobStatus, SKU, Skill, Token
from app.infra.storage import StorageService
from app.runners.prompt_runner import PromptRunner

logger = logging.getLogger(__name__)


def execute_job(job_id_str: str) -> None:
    """RQ task 入口（同步），兼容独立 worker 进程。"""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_job(job_id_str))


async def run_job(job_id_str: str) -> None:
    """可直接 await 的异步入口，供 FastAPI BackgroundTasks 调用。"""
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
        sku_row = (await session.execute(select(SKU).where(SKU.id == token_row.sku_id))).scalar_one_or_none()

        # 构建最终 prompt：基础 prompt + 项目选项 prompt_addition + 用户自定义备注
        base_prompt = skill_row.prompt_template or "Restore and enhance this image."
        combined_prompt = _build_prompt(base_prompt, sku_row, job.inputs or {})

        # 标记运行中
        job.status = JobStatus.running
        job.started_at = datetime.now(timezone.utc)
        await session.commit()

        try:
            runner = PromptRunner()
            run_result = runner.run(
                job_id=str(job.id),
                skill={
                    "prompt_template": combined_prompt,
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


def _build_prompt(base_prompt: str, sku_row: SKU | None, inputs: dict) -> str:
    """根据用户选择的项目选项和备注，拼接最终 prompt。

    inputs 中可包含：
      - selected_options: list[str]  — 用户选择的选项 ID 列表
      - user_note: str               — 用户自定义备注
    """
    parts = [base_prompt.strip()]

    if sku_row and sku_row.project_id and sku_row.project:
        project_options = (sku_row.project.options or {}).get("option_groups", [])
        selected_ids: list[str] = inputs.get("selected_options", [])

        for group in project_options:
            gid = group.get("id", "")
            gtype = group.get("type", "toggle")

            if gtype == "toggle":
                # 布尔选项：selected_options 中包含 group_id 表示已选中
                if gid in selected_ids:
                    addition = group.get("prompt_addition", "")
                    if addition:
                        parts.append(addition.strip())

            elif gtype == "single_choice":
                choices = group.get("choices", [])
                # 在 selected_ids 中找到本组被选中的 choice_id
                selected_choice_id = next(
                    (sid for sid in selected_ids if any(c.get("id") == sid for c in choices)),
                    group.get("default"),
                )
                if selected_choice_id:
                    choice = next((c for c in choices if c.get("id") == selected_choice_id), None)
                    if choice:
                        addition = choice.get("prompt_addition", "")
                        if addition:
                            parts.append(addition.strip())

    user_note = (inputs.get("user_note") or "").strip()
    if user_note:
        parts.append(f"用户特别要求：{user_note}")

    return "。".join(filter(None, parts))
