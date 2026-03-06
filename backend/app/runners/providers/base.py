"""Provider 抽象基类 — 从 runners.base 统一导出，保持向后兼容。"""

from app.runners.base import BaseProvider, ProviderResult  # noqa: F401
