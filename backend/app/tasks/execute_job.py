"""RQ 任务：执行 Job，自动 finalize。

RQ 运行同步函数，通过 asyncio.run() 桥接 async ORM。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import sys
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select

from app.core.config import settings
from app.domain.models import Asset, Job, JobStatus, SKU, Skill, Token
from app.infra.storage import StorageService
from app.runners.prompt_runner import PromptRunner

logger = logging.getLogger(__name__)


def _now() -> str:
    """返回 UTC ISO8601 毫秒时间戳字符串。"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _entry(step: str, **kwargs) -> dict:
    """构造一条结构化日志条目。"""
    return {"ts": _now(), "step": step, **kwargs}


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
    job_logs: list[dict] = []
    t_job_start = time.perf_counter()

    job_logs.append(_entry("job_start", job_id=job_id_str))

    async with factory() as session:
        job = await _load_job(session, job_id)
        if not job:
            logger.error("Job not found: %s", job_id_str)
            return

        skill_row = (await session.execute(select(Skill).where(Skill.id == job.skill_id))).scalar_one()
        token_row = (await session.execute(select(Token).where(Token.id == job.token_id))).scalar_one()
        sku_row = (await session.execute(select(SKU).where(SKU.id == token_row.sku_id))).scalar_one_or_none()

        job_logs.append(_entry(
            "job_context",
            skill_id=str(job.skill_id),
            skill_name=skill_row.name,
            token_id=str(job.token_id),
            sku_id=str(token_row.sku_id) if token_row else None,
            inputs=job.inputs or {},
        ))

        # 构建最终 prompt：基础 prompt + 项目选项 prompt_addition + 用户自定义备注
        base_prompt = skill_row.prompt_template or "Restore and enhance this image."
        combined_prompt = _build_prompt(base_prompt, sku_row, job.inputs or {})

        job_logs.append(_entry(
            "prompt_built",
            base_prompt_len=len(base_prompt),
            combined_prompt_len=len(combined_prompt),
            combined_prompt=combined_prompt,
        ))

        # 标记运行中
        job.status = JobStatus.running
        job.started_at = datetime.now(timezone.utc)
        job_logs.append(_entry("job_status_changed", status="running"))
        job.log_text = json.dumps(job_logs, ensure_ascii=False)
        await session.commit()

        _MAX_RETRIES = 3
        _TIMEOUT_SECONDS = 180  # 3 分钟

        run_result = None
        try:
            for attempt in range(1, _MAX_RETRIES + 1):
                t_runner = time.perf_counter()
                try:
                    job_logs.append(_entry(
                        "runner_attempt_start",
                        attempt=attempt,
                        max_retries=_MAX_RETRIES,
                        timeout_seconds=_TIMEOUT_SECONDS,
                    ))
                    job.log_text = json.dumps(job_logs, ensure_ascii=False)
                    await session.commit()
                    runner = PromptRunner()
                    run_result = await asyncio.wait_for(
                        asyncio.to_thread(
                            runner.run,
                            job_id=str(job.id),
                            skill={
                                "prompt_template": combined_prompt,
                                "runner_config": skill_row.runner_config or {},
                            },
                            inputs=job.inputs or {},
                            storage=storage,
                        ),
                        timeout=_TIMEOUT_SECONDS,
                    )
                    runner_ms = round((time.perf_counter() - t_runner) * 1000, 1)
                    job_logs.append(_entry(
                        "runner_attempt_done",
                        attempt=attempt,
                        duration_ms=runner_ms,
                        asset_count=len(run_result.assets),
                    ))
                    job.log_text = json.dumps(job_logs, ensure_ascii=False)
                    await session.commit()
                    break  # 成功，退出重试循环

                except asyncio.TimeoutError:
                    elapsed_ms = round((time.perf_counter() - t_runner) * 1000, 1)
                    job_logs.append(_entry(
                        "runner_attempt_timeout",
                        attempt=attempt,
                        max_retries=_MAX_RETRIES,
                        timeout_seconds=_TIMEOUT_SECONDS,
                        elapsed_ms=elapsed_ms,
                    ))
                    job.log_text = json.dumps(job_logs, ensure_ascii=False)
                    await session.commit()
                    logger.warning(
                        "Job %s 第 %d/%d 次超时（%.0f ms）",
                        job_id_str, attempt, _MAX_RETRIES, elapsed_ms,
                    )
                    if attempt >= _MAX_RETRIES:
                        raise RuntimeError(
                            f"AI 处理超时（{_TIMEOUT_SECONDS}s），已重试 {_MAX_RETRIES} 次，放弃"
                        ) from None
                    await asyncio.sleep(2)

                except Exception as attempt_exc:
                    elapsed_ms = round((time.perf_counter() - t_runner) * 1000, 1)
                    job_logs.append(_entry(
                        "runner_attempt_failed",
                        attempt=attempt,
                        max_retries=_MAX_RETRIES,
                        error=str(attempt_exc),
                        error_type=type(attempt_exc).__name__,
                        elapsed_ms=elapsed_ms,
                    ))
                    job.log_text = json.dumps(job_logs, ensure_ascii=False)
                    await session.commit()
                    logger.warning(
                        "Job %s 第 %d/%d 次失败: %s",
                        job_id_str, attempt, _MAX_RETRIES, attempt_exc,
                    )
                    if attempt >= _MAX_RETRIES:
                        raise
                    await asyncio.sleep(2)

            # 合并 Runner 的详细日志（JSON list）到 job_logs
            try:
                runner_entries = json.loads(run_result.logs) if run_result.logs else []
                if isinstance(runner_entries, list):
                    job_logs.extend(runner_entries)
            except Exception:
                if run_result.logs:
                    job_logs.append(_entry("runner_logs_raw", text=run_result.logs))

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

            total_ms = round((time.perf_counter() - t_job_start) * 1000, 1)
            job_logs.append(_entry(
                "job_succeeded",
                output_hash=output_hash[:16] + "…",
                total_duration_ms=total_ms,
            ))

            job.status = JobStatus.succeeded
            job.result = {"assets": run_result.assets, "metadata": run_result.metadata}
            job.log_text = json.dumps(job_logs, ensure_ascii=False, indent=2)
            job.output_hash = output_hash
            job.finished_at = datetime.now(timezone.utc)

            # finalize token（确认扣次数）
            token_row.used_count += 1
            token_row.reserved_count = max(0, token_row.reserved_count - 1)

            logger.info("Job %s succeeded (%.0f ms)", job_id_str, total_ms)

        except Exception as exc:
            total_ms = round((time.perf_counter() - t_job_start) * 1000, 1)
            job_logs.append(_entry(
                "job_failed",
                error=str(exc),
                error_type=type(exc).__name__,
                total_duration_ms=total_ms,
            ))

            logger.exception("Job %s failed: %s", job_id_str, exc)
            job.status = JobStatus.failed
            job.error = str(exc)
            job.log_text = json.dumps(job_logs, ensure_ascii=False, indent=2)
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
