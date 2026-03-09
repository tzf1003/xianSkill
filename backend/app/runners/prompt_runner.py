"""PromptRunner — 图像类 Skill 执行主干。

流程：
1. 从 MinIO 下载输入图像（inputs.image_key）
2. 调用 GeminiProvider 进行 AI 处理（GEMINI_API_KEY 未配置时降级至 MockProvider）
3. 将结果上传回 MinIO（jobs/{job_id}/result.png）
4. 返回 RunResult（含 asset 元数据 + 结构化 JSON 日志）
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timezone

from app.core.config import settings
from app.runners.base import BaseRunner, RunResult
from app.services.ai_provider_service import AIRuntimeConfig, current_env_runtime_config

logger = logging.getLogger(__name__)


def _now() -> str:
    """返回 UTC ISO8601 时间戳字符串。"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _entry(step: str, **kwargs) -> dict:
    """构造一条结构化日志条目。"""
    return {"ts": _now(), "step": step, **kwargs}


def _make_provider(ai_config: AIRuntimeConfig | None = None):
    """根据运行时配置选择 Provider；项目显式配置缺失时直接报错，env 缺失时降级 Mock。"""
    config = ai_config or current_env_runtime_config()
    protocol = (config.protocol or "gemini").lower()
    key = (config.api_key or "").strip()

    if not key or key.startswith("your-"):
        if ai_config is not None:
            raise RuntimeError("项目绑定的 AI 服务商缺少有效 API Key")
        logger.warning("%s API Key 未配置，降级使用 MockProvider", protocol.upper())
        from app.runners.providers.mock import MockProvider
        return MockProvider(), config

    if protocol == "openai":
        from app.runners.providers.openai_provider import OpenAIProvider
        logger.info("Provider: OpenAIProvider (model=%s)", config.model)
        return OpenAIProvider(config), config

    if protocol == "anthropic":
        from app.runners.providers.anthropic_provider import AnthropicProvider
        logger.info("Provider: AnthropicProvider (model=%s)", config.model)
        return AnthropicProvider(config), config

    if protocol == "volcengine":
        from app.runners.providers.volcengine_provider import VolcengineProvider
        logger.info("Provider: VolcengineProvider (model=%s)", config.model)
        return VolcengineProvider(config), config

    from app.runners.providers.gemini import GeminiProvider
    logger.info("Provider: GeminiProvider (model=%s)", config.model)
    return GeminiProvider(config), config


class PromptRunner(BaseRunner):
    def run(
        self,
        job_id: str,
        skill: dict,
        inputs: dict,
        storage,
    ) -> RunResult:
        logs: list[dict] = []
        t_runner_start = time.perf_counter()

        prompt = skill.get("prompt_template") or "Restore and enhance this image."
        image_key: str | None = inputs.get("image_key")
        ai_config_dict = skill.get("ai_config") or None
        ai_config = AIRuntimeConfig.from_dict(ai_config_dict) if ai_config_dict else None
        _, resolved_ai = _make_provider(ai_config)

        # ── 记录：运行开始 ────────────────────────────────────────────
        logs.append(_entry(
            "runner_start",
            job_id=job_id,
            api_format=resolved_ai.protocol,
            ai_source=resolved_ai.source,
            ai_provider=resolved_ai.provider_name,
            ai_model=resolved_ai.model,
            image_key=image_key,
            prompt_len=len(prompt),
        ))

        # ── 记录：完整 prompt ─────────────────────────────────────────
        logs.append(_entry(
            "prompt",
            full_prompt=prompt,
            prompt_len=len(prompt),
        ))

        # ── 1. 从 MinIO 下载输入图像 ──────────────────────────────────
        image_bytes: bytes | None = None
        if image_key:
            logs.append(_entry("download_start", image_key=image_key))
            t0 = time.perf_counter()
            try:
                image_bytes = storage.get_bytes(image_key)
                dl_ms = round((time.perf_counter() - t0) * 1000, 1)
                logs.append(_entry(
                    "download_done",
                    image_key=image_key,
                    size_bytes=len(image_bytes),
                    duration_ms=dl_ms,
                ))
                logger.info(
                    "Downloaded input image: %s (%d bytes, %.0f ms)",
                    image_key, len(image_bytes), dl_ms,
                )
            except Exception as exc:
                dl_ms = round((time.perf_counter() - t0) * 1000, 1)
                logs.append(_entry(
                    "download_error",
                    image_key=image_key,
                    error=str(exc),
                    duration_ms=dl_ms,
                ))
                logger.warning("Could not download image_key=%s: %s", image_key, exc)
        else:
            logs.append(_entry("download_skip", reason="no image_key in inputs"))

        # ── 2. 调用 Provider 处理图像 ─────────────────────────────────
        provider, resolved_ai = _make_provider(ai_config)
        provider_name = type(provider).__name__

        logs.append(_entry(
            "llm_request",
            provider=provider_name,
            model=resolved_ai.model,
            protocol=resolved_ai.protocol,
            prompt_len=len(prompt),
            input_image_bytes=len(image_bytes) if image_bytes else 0,
        ))

        t0 = time.perf_counter()
        provider_result = provider.complete(prompt, image_bytes)
        call_ms = round((time.perf_counter() - t0) * 1000, 1)

        logs.append(_entry(
            "llm_response",
            provider=provider_name,
            model=provider_result.model,
            finish_reason=provider_result.finish_reason,
            output_image_bytes=provider_result.output_image_bytes,
            response_text=provider_result.response_text or "",
            duration_ms=provider_result.duration_ms,  # 实际 API 耗时（provider 内部计时）
            total_call_ms=call_ms,  # 含序列化开销
            extra=provider_result.extra,
        ))
        logger.info(
            "LLM response: provider=%s model=%s finish=%s output=%d bytes duration=%.0f ms",
            provider_name,
            provider_result.model,
            provider_result.finish_reason,
            provider_result.output_image_bytes,
            provider_result.duration_ms,
        )

        result_bytes = provider_result.image_bytes

        # ── 3. 将处理结果上传至 MinIO ─────────────────────────────────
        result_key = f"jobs/{job_id}/result.png"
        logs.append(_entry("upload_start", result_key=result_key, size_bytes=len(result_bytes)))
        t0 = time.perf_counter()
        storage.put_bytes(result_key, result_bytes, "image/png")
        up_ms = round((time.perf_counter() - t0) * 1000, 1)
        logs.append(_entry(
            "upload_done",
            result_key=result_key,
            size_bytes=len(result_bytes),
            duration_ms=up_ms,
        ))
        logger.info("Uploaded result: %s (%d bytes, %.0f ms)", result_key, len(result_bytes), up_ms)

        # ── 4. 计算哈希 ───────────────────────────────────────────────
        result_hash = hashlib.sha256(result_bytes).hexdigest()
        total_ms = round((time.perf_counter() - t_runner_start) * 1000, 1)

        logs.append(_entry(
            "runner_done",
            result_key=result_key,
            result_hash=result_hash[:16] + "…",
            total_duration_ms=total_ms,
        ))

        return RunResult(
            assets=[
                {
                    "filename": "result.png",
                    "storage_key": result_key,
                    "content_type": "image/png",
                    "size_bytes": len(result_bytes),
                    "hash": result_hash,
                }
            ],
            logs=json.dumps(logs, ensure_ascii=False, indent=2),
            metadata={
                "prompt_used": prompt[:120],
                "provider": provider_name,
                "model": provider_result.model,
                "ai_protocol": resolved_ai.protocol,
                "ai_provider": resolved_ai.provider_name,
                "ai_source": resolved_ai.source,
                "llm_duration_ms": provider_result.duration_ms,
                "total_duration_ms": total_ms,
            },
            success=True,
        )

