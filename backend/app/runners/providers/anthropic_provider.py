"""AnthropicProvider — 使用 Anthropic / Anthropic-Compatible API 进行图像处理。

支持：
- 标准 Anthropic messages 格式（/v1/messages）
- 图像输入：将图片以 base64 source 方式嵌入消息
- 图像输出：若响应 content 包含 image 类型块（部分兼容代理支持），则提取返回
- 可通过 ANTHROPIC_BASE_URL 指向任意 Anthropic-Compatible 代理
- 原生 Claude 不生成图像，适合仅用于图像理解场景的兼容代理
"""

from __future__ import annotations

import base64
import io
import logging
import time

from PIL import Image

from app.runners.base import BaseProvider, ProviderResult
from app.services.ai_provider_service import AIRuntimeConfig

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseProvider):
    """使用 Anthropic / Anthropic-Compatible API 处理图像。"""

    def __init__(self, config: AIRuntimeConfig):
        self.config = config

    def complete(self, prompt: str, image_bytes: bytes | None = None) -> ProviderResult:
        if not self.config.api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY 未配置，请在 .env 中设置 ANTHROPIC_API_KEY"
            )

        try:
            import anthropic  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "anthropic 未安装，请执行: pip install anthropic"
            ) from exc

        client_kwargs: dict = {"api_key": self.config.api_key}
        if self.config.base_url:
            client_kwargs["base_url"] = self.config.base_url

        client = anthropic.Anthropic(**client_kwargs)

        # 构建消息 content
        content: list = []
        input_mime = ""
        if image_bytes:
            try:
                img_obj = Image.open(io.BytesIO(image_bytes))
                fmt = (img_obj.format or "JPEG").upper()
                input_mime = f"image/{fmt.lower()}"
            except Exception:
                input_mime = "image/jpeg"

            b64 = base64.standard_b64encode(image_bytes).decode()
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": input_mime,
                    "data": b64,
                },
            })

        content.append({"type": "text", "text": prompt})

        logger.info(
            "Anthropic 请求: model=%s, has_image=%s, input_mime=%s, input_size=%d bytes, "
            "prompt_len=%d\n--- PROMPT ---\n%s\n--- END PROMPT ---",
            self.config.model,
            image_bytes is not None,
            input_mime,
            len(image_bytes) if image_bytes else 0,
            len(prompt),
            prompt,
        )

        t0 = time.perf_counter()
        response = client.messages.create(
            model=self.config.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": content}],
        )
        duration_ms = (time.perf_counter() - t0) * 1000

        finish_reason = response.stop_reason or ""

        # ── 尝试从响应中提取图像数据 ─────────────────────────────────
        # 标准 Claude 只返回文本；部分兼容代理（转发图像生成模型）可能返回 image 块
        text_parts: list[str] = []
        for block in response.content:
            block_type = getattr(block, "type", None)

            if block_type == "image":
                src = getattr(block, "source", None)
                if src and getattr(src, "type", None) == "base64":
                    raw = base64.b64decode(src.data)
                    result_img = Image.open(io.BytesIO(raw))
                    buf = io.BytesIO()
                    result_img.save(buf, format="PNG")
                    png_bytes = buf.getvalue()
                    logger.info(
                        "Anthropic 返回图像（base64）: %d bytes, duration=%.0f ms",
                        len(png_bytes), duration_ms,
                    )
                    return ProviderResult(
                        image_bytes=png_bytes,
                        model=self.config.model,
                        finish_reason=finish_reason,
                        response_text="",
                        image_mime="image/png",
                        prompt_len=len(prompt),
                        input_image_bytes=len(image_bytes) if image_bytes else 0,
                        output_image_bytes=len(png_bytes),
                        duration_ms=round(duration_ms, 1),
                        extra={"input_mime": input_mime},
                    )
            elif block_type == "text":
                text_parts.append(getattr(block, "text", ""))

        # ── 纯文本响应，无法获取图像 ──────────────────────────────────
        text_preview = " | ".join(text_parts)[:300]
        logger.error(
            "Anthropic 未返回图像！model=%s, finish_reason=%s, duration=%.0f ms, 文本响应: %s",
            self.config.model,
            finish_reason,
            duration_ms,
            text_preview,
        )
        raise RuntimeError(
            f"Anthropic 未返回图像数据（model={self.config.model}, "
            f"finish_reason={finish_reason}）。"
            f"文本响应: {text_preview[:200]}"
        )
