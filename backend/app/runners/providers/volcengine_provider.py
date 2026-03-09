from __future__ import annotations

import base64
import io
import logging
import time

from PIL import Image

from app.runners.base import BaseProvider, ProviderResult
from app.services.ai_provider_service import AIRuntimeConfig

logger = logging.getLogger(__name__)


class VolcengineProvider(BaseProvider):
    """使用火山方舟 Ark SDK 进行图像生成/编辑。"""

    def __init__(self, config: AIRuntimeConfig):
        self.config = config

    def complete(self, prompt: str, image_bytes: bytes | None = None) -> ProviderResult:
        if not self.config.api_key:
            raise RuntimeError("VOLCENGINE_API_KEY 未配置，请在 .env 中设置 VOLCENGINE_API_KEY")

        try:
            from volcenginesdkarkruntime import Ark  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError("volcengine-python-sdk[ark] 未安装，请执行: pip install 'volcengine-python-sdk[ark]'") from exc

        client = Ark(
            api_key=self.config.api_key,
            base_url=self.config.base_url or "https://ark.cn-beijing.volces.com/api/v3",
            timeout=600.0,
        )

        if not hasattr(client, "images"):
            raise RuntimeError(
                "当前 volcengine-python-sdk 版本不支持 Ark 图片接口。"
                "请升级到 >=5,<6 后重试。"
            )

        input_mime = ""
        image_input: str | None = None
        request_size = "2K"
        if image_bytes:
            try:
                img_obj = Image.open(io.BytesIO(image_bytes))
                fmt = (img_obj.format or "PNG").upper()
                input_mime = f"image/{fmt.lower()}"
            except Exception:
                input_mime = "image/png"

            b64 = base64.b64encode(image_bytes).decode("utf-8")
            image_input = f"data:{input_mime};base64,{b64}"

        logger.info(
            "Volcengine 请求: model=%s, has_image=%s, input_mime=%s, input_size=%d bytes, request_size=%s, prompt_len=%d",
            self.config.model,
            image_bytes is not None,
            input_mime,
            len(image_bytes) if image_bytes else 0,
            request_size,
            len(prompt),
        )

        t0 = time.perf_counter()
        response = client.images.generate(
            model=self.config.model,
            prompt=prompt,
            image=image_input,
            response_format="b64_json",
            size=request_size,
            watermark=False,
            output_format="png",
        )
        duration_ms = (time.perf_counter() - t0) * 1000

        error = getattr(response, "error", None)
        if error and getattr(error, "message", None):
            raise RuntimeError(f"火山方舟图片生成失败: {error.message}")

        data = getattr(response, "data", None) or []
        if not data:
            raise RuntimeError(f"火山方舟未返回图像数据（model={self.config.model}）")

        first = data[0]
        b64_json = getattr(first, "b64_json", None) or ""
        image_url = getattr(first, "url", None) or ""

        raw: bytes
        if b64_json:
            raw = base64.b64decode(b64_json)
        else:
            raise RuntimeError(
                f"火山方舟未返回 b64_json 图像数据（model={self.config.model}）。"
                f"image_url={bool(image_url)}"
            )

        result_img = Image.open(io.BytesIO(raw))
        buf = io.BytesIO()
        result_img.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        usage = getattr(response, "usage", None)
        logger.info(
            "Volcengine 返回图像: model=%s size=%d bytes duration=%.0f ms",
            self.config.model,
            len(png_bytes),
            duration_ms,
        )
        return ProviderResult(
            image_bytes=png_bytes,
            model=self.config.model,
            finish_reason="completed",
            response_text="",
            image_mime="image/png",
            prompt_len=len(prompt),
            input_image_bytes=len(image_bytes) if image_bytes else 0,
            output_image_bytes=len(png_bytes),
            duration_ms=round(duration_ms, 1),
            extra={
                "input_mime": input_mime,
                "request_size": request_size,
                "usage": self._usage_to_dict(usage),
                "source": "b64_json" if b64_json else "url",
            },
        )

    def _usage_to_dict(self, usage) -> dict:
        if usage is None:
            return {}
        result = {}
        for key in ("generated_images", "output_tokens", "total_tokens"):
            value = getattr(usage, key, None)
            if value is not None:
                result[key] = value
        return result