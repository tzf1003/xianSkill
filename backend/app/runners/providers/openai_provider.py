"""OpenAIProvider — 使用 OpenAI / OpenAI-Compatible API 进行图像处理。

支持：
- 标准 OpenAI chat completions 格式（/v1/chat/completions）
- 图像输入：将图片以 base64 data URI 方式嵌入消息
- 图像输出：若响应 content 块中含 image_url（data URI），则提取并返回图像
- 可通过 OPENAI_BASE_URL 指向任意 OpenAI-Compatible 代理
"""

from __future__ import annotations

import base64
import io
import logging
import re
import time

from PIL import Image

from app.runners.base import BaseProvider, ProviderResult
from app.services.ai_provider_service import AIRuntimeConfig

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """使用 OpenAI / OpenAI-Compatible API 处理图像。"""

    def __init__(self, config: AIRuntimeConfig):
        self.config = config

    def complete(self, prompt: str, image_bytes: bytes | None = None) -> ProviderResult:
        if not self.config.api_key:
            raise RuntimeError(
                "OPENAI_API_KEY 未配置，请在 .env 中设置 OPENAI_API_KEY"
            )

        try:
            from openai import OpenAI  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "openai 未安装，请执行: pip install openai"
            ) from exc

        client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url or None,
            timeout=600.0,
        )

        # 构建消息 content（文本在前，图像在后）
        content: list = []
        input_mime = ""

        content.append({"type": "text", "text": prompt})

        if image_bytes:
            # 校验是否为真实图片，防止伪造后缀上传非图片文件
            _SUPPORTED_MIMES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
            try:
                img_obj = Image.open(io.BytesIO(image_bytes))
                img_obj.verify()  # 校验图片数据完整性
                # verify() 后需重新打开获取 format
                img_obj = Image.open(io.BytesIO(image_bytes))
                fmt = (img_obj.format or "JPEG").upper()
                input_mime = f"image/{fmt.lower()}"
            except Exception:
                raise RuntimeError(
                    "上传的文件不是有效的图片格式，请上传 JPEG/PNG/GIF/WebP 图片"
                )
            if input_mime not in _SUPPORTED_MIMES:
                input_mime = "image/jpeg"
                input_mime = "image/jpeg"

            b64 = base64.standard_b64encode(image_bytes).decode()
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{input_mime};base64,{b64}"},
            })

        logger.info(
            "OpenAI 请求: model=%s, has_image=%s, input_mime=%s, input_size=%d bytes, "
            "prompt_len=%d\n--- PROMPT ---\n%s\n--- END PROMPT ---",
            self.config.model,
            image_bytes is not None,
            input_mime,
            len(image_bytes) if image_bytes else 0,
            len(prompt),
            prompt,
        )

        t0 = time.perf_counter()
        stream = client.chat.completions.create(
            model=self.config.model,
            messages=[{"role": "user", "content": content}],
            stream=True,
            stream_options={"include_usage": True},
        )

        # 收集流式响应
        full_text = ""
        finish_reason = ""
        for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    full_text += delta.content
                if chunk.choices[0].finish_reason:
                    finish_reason = chunk.choices[0].finish_reason
        duration_ms = (time.perf_counter() - t0) * 1000

        msg_content = full_text

        # ── 从流式响应文本中提取图像数据 ────────────────────────────
        def _try_extract_b64(data_uri: str) -> bytes | None:
            """从 data URI 中提取 base64 并解码，失败返回 None。"""
            try:
                _, b64_part = data_uri.split(",", 1)
                return base64.b64decode(b64_part + "==")  # 补齐 padding
            except Exception:
                return None

        def _bytes_to_png(raw: bytes) -> bytes:
            result_img = Image.open(io.BytesIO(raw))
            buf = io.BytesIO()
            result_img.save(buf, format="PNG")
            return buf.getvalue()

        if msg_content:
            # 尝试 Markdown 格式：![...](data:image/xxx;base64,...)
            md_match = re.search(r'!\[[^\]]*\]\((data:image/[^;]+;base64,[A-Za-z0-9+/=\s]+)\)', msg_content)
            if not md_match:
                # 尝试裸 data URI
                md_match = re.search(r'(data:image/[^;]+;base64,[A-Za-z0-9+/=\s]+)', msg_content)

            if md_match:
                data_uri = md_match.group(1).replace("\n", "").replace(" ", "")
                raw = _try_extract_b64(data_uri)
                if raw:
                    try:
                        png_bytes = _bytes_to_png(raw)
                        logger.info(
                            "OpenAI 返回图像（文本 data URI）: %d bytes, duration=%.0f ms",
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
                            extra={"input_mime": input_mime, "extracted_from": "text"},
                        )
                    except Exception as e:
                        logger.warning("从文本 data URI 解析图像失败: %s", e)

        # ── 纯文本响应，无法获取图像 ──────────────────────────────────
        text_preview = msg_content if isinstance(msg_content, str) else str(msg_content)
        logger.error(
            "OpenAI 未返回图像！model=%s, finish_reason=%s, duration=%.0f ms, 文本响应: %s",
            self.config.model,
            finish_reason,
            duration_ms,
            text_preview[:300],
        )
        raise RuntimeError(
            f"OpenAI 未返回图像数据（model={self.config.model}, "
            f"finish_reason={finish_reason}）。"
            f"文本响应: {text_preview[:200]}"
        )
