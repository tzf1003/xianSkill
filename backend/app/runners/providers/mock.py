"""MockProvider — 使用 Pillow 做灰度化模拟 AI 修复效果。"""

from __future__ import annotations

import io
import time

from PIL import Image, ImageDraw, ImageFont

from app.runners.base import BaseProvider, ProviderResult


class MockProvider(BaseProvider):
    """
    Mock AI Provider：
    - 将彩色图像转换为灰度图（模拟"风格化处理"）
    - 在右下角加上水印文字 [MOCK RESTORED]
    - 输出 PNG
    """

    def complete(self, prompt: str, image_bytes: bytes | None = None) -> ProviderResult:
        t0 = time.perf_counter()
        if image_bytes:
            img = Image.open(io.BytesIO(image_bytes)).convert("L").convert("RGB")
        else:
            # 无图时生成纯色占位图
            img = Image.new("RGB", (512, 512), color=(200, 200, 200))

        draw = ImageDraw.Draw(img)
        draw.text((10, img.height - 24), "[MOCK RESTORED]", fill=(255, 80, 80))

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_bytes = buf.getvalue()
        duration_ms = (time.perf_counter() - t0) * 1000

        return ProviderResult(
            image_bytes=png_bytes,
            model="mock",
            finish_reason="STOP",
            response_text="",
            image_mime="image/png",
            prompt_len=len(prompt),
            input_image_bytes=len(image_bytes) if image_bytes else 0,
            output_image_bytes=len(png_bytes),
            duration_ms=round(duration_ms, 1),
        )
