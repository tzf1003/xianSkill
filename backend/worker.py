"""RQ Worker 入口 — 从 backend/ 目录运行：python worker.py"""

from __future__ import annotations

import asyncio
import os
import sys

# 确保 backend/ 在 Python 路径中
sys.path.insert(0, os.path.dirname(__file__))

# Windows: 切换为 SelectorEventLoop，兼容 asyncpg 与 Docker port-forwarding
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import redis
from rq import Queue, Worker
from rq.timeouts import BaseDeathPenalty
from rq.worker import SimpleWorker

from app.core.config import settings


class _NoopDeathPenalty(BaseDeathPenalty):
    """Windows 无 SIGALRM，用空实现替代超时机制。"""

    def setup_death_penalty(self) -> None:
        pass

    def cancel_death_penalty(self) -> None:
        pass


class _WindowsSimpleWorker(SimpleWorker):
    """Windows 专用 Worker：禁用依赖 SIGALRM 的超时机制。"""
    death_penalty_class = _NoopDeathPenalty


if __name__ == "__main__":
    conn = redis.from_url(settings.REDIS_URL)
    queues = [Queue("default", connection=conn)]
    if sys.platform == "win32":
        worker = _WindowsSimpleWorker(queues, connection=conn)
    else:
        worker = Worker(queues, connection=conn)
    print(f"[worker] Connected to Redis: {settings.REDIS_URL}")
    print("[worker] Listening on queue: default")
    worker.work()
