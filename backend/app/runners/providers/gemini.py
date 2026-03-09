"""GeminiProvider — 调用 Google Gemini API 进行图像处理。

支持：
- 图像处理模式：输入图像 + Prompt → 输出处理后的图像
  model: GEMINI_IMAGE_MODEL（需支持 IMAGE 响应模态）
- Gemini 未返回图像时抛出 RuntimeError，Job 明确标记为 failed，不静默降级返回原图
"""

from __future__ import annotations

import io
import logging
import time

from PIL import Image

from app.runners.base import BaseProvider, ProviderResult
from app.runners.providers.image_utils import prepare_input_image
from app.services.ai_provider_service import AIRuntimeConfig

logger = logging.getLogger(__name__)


class GeminiProvider(BaseProvider):
    """使用 Google Gemini API（google-genai SDK）处理图像。"""

    def __init__(self, config: AIRuntimeConfig):
        self.config = config

    def complete(self, prompt: str, image_bytes: bytes | None = None) -> ProviderResult:
        if not self.config.api_key:
            raise RuntimeError(
                "GEMINI_API_KEY 未配置，请在 .env 中设置 GEMINI_API_KEY"
            )

        # 延迟导入，避免未安装时影响其他功能
        try:
            from google import genai  # type: ignore[import]
            from google.genai import types  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "google-genai 未安装，请执行: pip install google-genai"
            ) from exc

        http_options = types.HttpOptions(base_url=self.config.base_url) if self.config.base_url else None
        client = genai.Client(
            api_key=self.config.api_key,
            http_options=http_options,
        )

        # 构建 contents
        contents: list = []
        input_mime = ""
        original_input_mime = ""
        request_image_bytes = image_bytes
        if image_bytes:
            prepared = prepare_input_image(
                image_bytes,
                supported_mimes={"image/jpeg", "image/png", "image/webp"},
            )
            request_image_bytes = prepared.data
            input_mime = prepared.mime
            original_input_mime = prepared.original_mime

            contents.append(
                types.Part.from_bytes(data=request_image_bytes, mime_type=input_mime)
            )

        contents.append(prompt)

        logger.info(
            "Gemini 请求: model=%s, has_image=%s, input_mime=%s, input_size=%d bytes, "
            "prompt_len=%d\n--- PROMPT ---\n%s\n--- END PROMPT ---",
            self.config.model,
            image_bytes is not None,
            input_mime,
            len(request_image_bytes) if request_image_bytes else 0,
            len(prompt),
            prompt,
        )

        t0 = time.perf_counter()
        response = client.models.generate_content(
            model=self.config.model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
            ),
        )
        duration_ms = (time.perf_counter() - t0) * 1000

        # ── 检查 candidates ───────────────────────────────────────────
        if not response.candidates:
            # prompt_feedback 可能包含 SAFETY 屏蔽原因
            feedback = getattr(response, "prompt_feedback", None)
            block_reason = getattr(feedback, "block_reason", None) if feedback else None
            raise RuntimeError(
                f"Gemini 返回空 candidates（model={self.config.model}）。"
                f"可能被安全策略屏蔽，block_reason={block_reason}"
            )

        candidate = response.candidates[0]
        finish_reason = getattr(candidate, "finish_reason", None)
        finish_reason_str = str(finish_reason) if finish_reason else ""

        # finish_reason: SAFETY / RECITATION / OTHER 表示被拒绝
        if finish_reason and finish_reason_str not in ("FinishReason.STOP", "STOP", "1"):
            raise RuntimeError(
                f"Gemini 终止原因异常: finish_reason={finish_reason}（model={self.config.model}）。"
                f"请检查图片内容或 prompt 是否触发了安全策略"
            )

        # content 可能为 None（safety block 时）
        if candidate.content is None or not candidate.content.parts:
            raise RuntimeError(
                f"Gemini 返回空 content（model={self.config.model}, "
                f"finish_reason={finish_reason}）"
            )

        # ── 从响应中提取图像数据 ──────────────────────────────────────
        text_parts: list[str] = []
        for part in candidate.content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                response_mime = part.inline_data.mime_type
                raw_size = len(part.inline_data.data)
                logger.info(
                    "Gemini 返回图像: mime=%s, raw_size=%d bytes, duration=%.0f ms",
                    response_mime,
                    raw_size,
                    duration_ms,
                )
                # 统一转为 PNG 输出
                result_img = Image.open(io.BytesIO(part.inline_data.data))
                buf = io.BytesIO()
                result_img.save(buf, format="PNG")
                png_bytes = buf.getvalue()
                logger.info(
                    "Gemini 响应图像转换为 PNG: %d bytes", len(png_bytes)
                )
                return ProviderResult(
                    image_bytes=png_bytes,
                    model=self.config.model,
                    finish_reason=finish_reason_str,
                    response_text="",
                    image_mime="image/png",
                    prompt_len=len(prompt),
                    input_image_bytes=len(image_bytes) if image_bytes else 0,
                    output_image_bytes=len(png_bytes),
                    duration_ms=round(duration_ms, 1),
                    extra={
                        "candidates_count": len(response.candidates),
                        "input_mime": input_mime,
                        "original_input_mime": original_input_mime,
                        "input_transcoded": bool(image_bytes) and request_image_bytes != image_bytes,
                    },
                )
            elif hasattr(part, "text") and part.text:
                text_parts.append(part.text)

        # Gemini 只返回了文字，未返回图像 → 明确报错
        text_preview = " | ".join(text_parts)[:300]
        logger.error(
            "Gemini 未返回图像！model=%s, finish_reason=%s, duration=%.0f ms, 文本响应: %s",
            self.config.model,
            finish_reason,
            duration_ms,
            text_preview,
        )
        raise RuntimeError(
            f"Gemini 未返回图像数据（model={self.config.model}, "
            f"finish_reason={finish_reason}）。"
            f"Gemini 文字响应: {text_preview[:200]}"
        )
