"""GeminiProvider — 调用 Google Gemini API 进行图像处理。

支持：
- 图像处理模式：输入图像 + Prompt → 输出处理后的图像
  model: GEMINI_IMAGE_MODEL（需支持 IMAGE 响应模态，如 gemini-2.0-flash-preview-image-generation）
- 如果 Gemini 未返回图像（比如模型不支持），自动降级：将文本响应记录 log，
  原图原样返回，并以 JPEG 格式输出（保证 PromptRunner 不崩溃）
"""

from __future__ import annotations

import io
import logging

from PIL import Image

from app.core.config import settings
from app.runners.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class GeminiProvider(BaseProvider):
    """使用 Google Gemini API（google-genai SDK）处理图像。"""

    def complete(self, prompt: str, image_bytes: bytes | None = None) -> bytes:
        if not settings.GEMINI_API_KEY:
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

        client = genai.Client(
            api_key=settings.GEMINI_API_KEY,
        )

        # 构建 contents
        contents: list = []
        if image_bytes:
            # 探测 MIME 类型
            try:
                img_obj = Image.open(io.BytesIO(image_bytes))
                fmt = (img_obj.format or "JPEG").upper()
                mime_type = f"image/{fmt.lower()}"
            except Exception:
                mime_type = "image/jpeg"

            contents.append(
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            )

        contents.append(prompt)

        logger.info(
            "Gemini 请求: model=%s, has_image=%s, prompt_len=%d, prompt_preview=%s",
            settings.GEMINI_IMAGE_MODEL,
            image_bytes is not None,
            len(prompt),
            prompt[:200],
        )

        response = client.models.generate_content(
            model=settings.GEMINI_IMAGE_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
            ),
        )

        # 从响应中提取图像数据
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                logger.info(
                    "Gemini 返回图像: mime=%s, size=%d bytes",
                    part.inline_data.mime_type,
                    len(part.inline_data.data),
                )
                # 统一转为 PNG 输出
                result_img = Image.open(io.BytesIO(part.inline_data.data))
                buf = io.BytesIO()
                result_img.save(buf, format="PNG")
                return buf.getvalue()

        # Gemini 没有返回图像 — 抛出异常让 Job 明确失败，不再静默降级返回原图
        text_parts = [
            p.text
            for p in response.candidates[0].content.parts
            if hasattr(p, "text") and p.text
        ]
        text_preview = " | ".join(text_parts)[:300]
        logger.error(
            "Gemini 未返回图像！model=%s, 文本响应: %s",
            settings.GEMINI_IMAGE_MODEL,
            text_preview,
        )
        raise RuntimeError(
            f"Gemini 未返回图像数据（model={settings.GEMINI_IMAGE_MODEL}）。"
            f"请确认模型支持图像输出，并检查 prompt 是否合规。文本响应: {text_preview[:200]}"
        )
