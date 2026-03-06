"""Runner 抽象基类与返回值数据类。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class RunResult:
    """Runner 的执行结果。"""

    assets: list[dict] = field(default_factory=list)
    """每个 asset 是 {filename, storage_key, content_type, size_bytes, hash}"""
    logs: str = ""
    cost: dict | None = None
    metadata: dict | None = None
    success: bool = True
    error: str | None = None


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
