"""MockProvider — 使用 Pillow 做灰度化模拟 AI 修复效果。"""

from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont

from app.runners.providers.base import BaseProvider


class MockProvider(BaseProvider):
    """
    Mock AI Provider：
    - 将彩色图像转换为灰度图（模拟"风格化处理"）
    - 在右下角加上水印文字 [MOCK RESTORED]
    - 输出 PNG
    """

    def complete(self, prompt: str, image_bytes: bytes | None = None) -> bytes:
        if image_bytes:
            img = Image.open(io.BytesIO(image_bytes)).convert("L").convert("RGB")
        else:
            # 无图时生成纯色占位图
            img = Image.new("RGB", (512, 512), color=(200, 200, 200))

        draw = ImageDraw.Draw(img)
        draw.text((10, img.height - 24), "[MOCK RESTORED]", fill=(255, 80, 80))

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
