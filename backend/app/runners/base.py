"""Runner / Provider 抽象基类与返回值数据类。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ProviderResult:
    """AI Provider 调用结果，包含图像数据与调用元数据。"""

    image_bytes: bytes
    """处理后的图像（PNG）"""
    model: str = ""
    """实际使用的模型名称"""
    finish_reason: str = ""
    """Gemini finish_reason 或等效标识"""
    response_text: str = ""
    """LLM 返回的文本部分（如有）"""
    image_mime: str = "image/png"
    """响应图像的 MIME 类型"""
    prompt_len: int = 0
    """发送 prompt 的字符数"""
    input_image_bytes: int = 0
    """输入图像大小（字节）"""
    output_image_bytes: int = 0
    """输出图像大小（字节）"""
    duration_ms: float = 0.0
    """API 调用耗时（毫秒）"""
    extra: dict = field(default_factory=dict)
    """额外信息，如 usage、候选数等"""


@dataclass
class RunResult:
    """Runner 的执行结果。"""

    assets: list[dict] = field(default_factory=list)
    """每个 asset 是 {filename, storage_key, content_type, size_bytes, hash}"""
    logs: str = ""
    """结构化 JSON 日志（list of log-entry dicts），供存入 job.log_text"""
    cost: dict | None = None
    metadata: dict | None = None
    success: bool = True
    error: str | None = None


class BaseProvider(ABC):
    """AI Provider 抽象基类。"""

    @abstractmethod
    def complete(self, prompt: str, image_bytes: bytes | None = None) -> ProviderResult:
        """
        执行 AI 补全。

        Args:
            prompt: 提示词
            image_bytes: 原始图像字节（可选，由 PromptRunner 已从 MinIO 下载）

        Returns:
            ProviderResult，包含处理后的图像字节与调用元数据
        """


class BaseRunner(ABC):
    """所有 Skill Runner 的抽象基类。"""

    @abstractmethod
    def run(
        self,
        job_id: str,
        skill: dict,
        inputs: dict,
        storage,
    ) -> RunResult:
        """同步执行 Skill 任务并返回结果。"""
