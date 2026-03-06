"""Provider 抽象基类 — AI 模型调用接口。"""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseProvider(ABC):
    @abstractmethod
    def complete(self, prompt: str, image_bytes: bytes | None = None) -> bytes:
        """
        执行 AI 补全。

        Args:
            prompt: 提示词
            image_bytes: 原始图像字节（可选，由 PromptRunner 已从 MinIO 下载）

        Returns:
            处理后的图像字节（PNG 格式）
        """
