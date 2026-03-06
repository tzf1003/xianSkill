"""PromptRunner — 图像类 Skill 执行主干。

流程：
1. 从 MinIO 下载输入图像（inputs.image_key）
2. 调用 GeminiProvider 进行 AI 处理（GEMINI_API_KEY 未配置时降级至 MockProvider）
3. 将结果上传回 MinIO（jobs/{job_id}/result.png）
4. 返回 RunResult（含 asset 元数据）
"""

from __future__ import annotations

import hashlib
import logging

from app.core.config import settings
from app.runners.base import BaseRunner, RunResult

logger = logging.getLogger(__name__)


def _make_provider():
    """根据配置选择 Provider：优先 Gemini，未配置或占位 API Key 则降级至 Mock。"""
    key = settings.GEMINI_API_KEY
    if key and key != "your-gemini-api-key-here":
        from app.runners.providers.gemini import GeminiProvider
        logger.info("Provider: GeminiProvider (model=%s)", settings.GEMINI_IMAGE_MODEL)
        return GeminiProvider()
    else:
        from app.runners.providers.mock import MockProvider
        logger.warning("GEMINI_API_KEY 未配置，降级使用 MockProvider")
        return MockProvider()


class PromptRunner(BaseRunner):
    def run(
        self,
        job_id: str,
        skill: dict,
        inputs: dict,
        storage,
    ) -> RunResult:
        prompt = skill.get("prompt_template") or "Restore and enhance this image."
        image_key: str | None = inputs.get("image_key")

        # 1. 从 MinIO 下载输入图像
        image_bytes: bytes | None = None
        if image_key:
            try:
                image_bytes = storage.get_bytes(image_key)
                logger.info(
                    "Downloaded input image: %s (%d bytes)", image_key, len(image_bytes)
                )
            except Exception as exc:
                logger.warning("Could not download image_key=%s: %s", image_key, exc)

        # 2. 调用 Provider 处理图像
        provider = _make_provider()
        result_bytes = provider.complete(prompt, image_bytes)

        provider_name = type(provider).__name__

        # 3. 将处理结果上传至 MinIO
        result_key = f"jobs/{job_id}/result.png"
        storage.put_bytes(result_key, result_bytes, "image/png")
        logger.info(
            "Uploaded result: %s (%d bytes)", result_key, len(result_bytes)
        )

        # 4. 计算哈希
        result_hash = hashlib.sha256(result_bytes).hexdigest()

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
            logs=(
                f"PromptRunner OK | provider={provider_name} "
                f"| input_key={image_key} | output_key={result_key}"
            ),
            metadata={
                "prompt_used": prompt[:120],
                "provider": provider_name,
                "gemini_image_model": settings.GEMINI_IMAGE_MODEL if settings.GEMINI_API_KEY else None,
            },
            success=True,
        )
