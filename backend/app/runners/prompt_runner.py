"""PromptRunner — 图像类 Skill 执行主干。

流程：
1. 从 MinIO 下载输入图像（inputs.image_key）
2. 调用 MockProvider 做灰度化处理
3. 将结果上传回 MinIO（jobs/{job_id}/result.png）
4. 返回 RunResult（含 asset 元数据）
"""

from __future__ import annotations

import hashlib
import logging

from app.runners.base import BaseRunner, RunResult
from app.runners.providers.mock import MockProvider

logger = logging.getLogger(__name__)


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

        # 1. 下载输入图像
        image_bytes: bytes | None = None
        if image_key:
            try:
                image_bytes = storage.get_bytes(image_key)
                logger.info("Downloaded input image: %s (%d bytes)", image_key, len(image_bytes))
            except Exception as exc:
                logger.warning("Could not download image_key=%s: %s", image_key, exc)

        # 2. 调用 mock provider
        provider = MockProvider()
        result_bytes = provider.complete(prompt, image_bytes)

        # 3. 上传结果
        result_key = f"jobs/{job_id}/result.png"
        storage.put_bytes(result_key, result_bytes, "image/png")
        logger.info("Uploaded result: %s (%d bytes)", result_key, len(result_bytes))

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
            logs=f"PromptRunner OK | provider=mock | input_key={image_key} | output_key={result_key}",
            metadata={"prompt_used": prompt[:120]},
            success=True,
        )
