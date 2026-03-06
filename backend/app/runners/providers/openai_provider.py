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

from app.core.config import settings
from app.runners.base import BaseProvider, ProviderResult

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """使用 OpenAI / OpenAI-Compatible API 处理图像。"""

    def complete(self, prompt: str, image_bytes: bytes | None = None) -> ProviderResult:
        if not settings.OPENAI_API_KEY:
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
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL or None,
        )

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
                "type": "image_url",
                "image_url": {"url": f"data:{input_mime};base64,{b64}"},
            })

        content.append({"type": "text", "text": prompt})

        logger.info(
            "OpenAI 请求: model=%s, has_image=%s, input_mime=%s, input_size=%d bytes, "
            "prompt_len=%d\n--- PROMPT ---\n%s\n--- END PROMPT ---",
            settings.OPENAI_IMAGE_MODEL,
            image_bytes is not None,
            input_mime,
            len(image_bytes) if image_bytes else 0,
            len(prompt),
            prompt,
        )

        t0 = time.perf_counter()
        response = client.chat.completions.create(
            model=settings.OPENAI_IMAGE_MODEL,
            messages=[{"role": "user", "content": content}],
        )
        duration_ms = (time.perf_counter() - t0) * 1000

        choice = response.choices[0]
        finish_reason = choice.finish_reason or ""
        msg_content = choice.message.content

        # ── 尝试从响应中提取图像数据 ─────────────────────────────────
        # 兼容以下场景：
        # 1. content 是 list，块类型为 image_url，值为 data URI
        # 2. content 是 list，块类型为 image_url，值为 https URL（不支持，记录警告）
        # 3. content 是纯字符串，包含 Markdown 图像 ![...](data:image/...;base64,...) 格式
        # 4. content 是纯字符串，包含裸 data URI（data:image/...;base64,...）
        def _try_extract_b64(data_uri: str) -> bytes | None:
            """从 data URI 中提取 base64 并解码，失败返回 None。"""
            try:
                _, b64_part = data_uri.split(",", 1)
                # base64 payload 可能被截断显示，但实际响应是完整的
                return base64.b64decode(b64_part + "==")  # 补齐 padding
            except Exception:
                return None

        def _bytes_to_png(raw: bytes) -> bytes:
            result_img = Image.open(io.BytesIO(raw))
            buf = io.BytesIO()
            result_img.save(buf, format="PNG")
            return buf.getvalue()

        if isinstance(msg_content, list):
            for block in msg_content:
                block_type = block.get("type") if isinstance(block, dict) else getattr(block, "type", None)
                if block_type == "image_url":
                    url_obj = block.get("image_url") if isinstance(block, dict) else getattr(block, "image_url", None)
                    url = (url_obj.get("url") if isinstance(url_obj, dict) else getattr(url_obj, "url", "")) or ""
                    if url.startswith("data:image/"):
                        raw = _try_extract_b64(url)
                        if raw:
                            png_bytes = _bytes_to_png(raw)
                            logger.info(
                                "OpenAI 返回图像（list image_url data URI）: %d bytes, duration=%.0f ms",
                                len(png_bytes), duration_ms,
                            )
                            return ProviderResult(
                                image_bytes=png_bytes,
                                model=settings.OPENAI_IMAGE_MODEL,
                                finish_reason=finish_reason,
                                response_text="",
                                image_mime="image/png",
                                prompt_len=len(prompt),
                                input_image_bytes=len(image_bytes) if image_bytes else 0,
                                output_image_bytes=len(png_bytes),
                                duration_ms=round(duration_ms, 1),
                                extra={"input_mime": input_mime},
                            )
                    elif url.startswith("https://"):
                        logger.warning("OpenAI 返回了 URL 图像，暂不支持下载: %s", url[:100])

        # ── 纯文本中提取图像（Markdown / 裸 data URI） ───────────────
        if isinstance(msg_content, str):
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
                            model=settings.OPENAI_IMAGE_MODEL,
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
            settings.OPENAI_IMAGE_MODEL,
            finish_reason,
            duration_ms,
            text_preview[:300],
        )
        raise RuntimeError(
            f"OpenAI 未返回图像数据（model={settings.OPENAI_IMAGE_MODEL}, "
            f"finish_reason={finish_reason}）。"
            f"文本响应: {text_preview[:200]}"
        )
