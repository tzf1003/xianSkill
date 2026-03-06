"""RQ 任务队列工厂。"""

from __future__ import annotations

import redis
from rq import Queue

from app.core.config import settings


def get_queue() -> Queue:
    """创建并返回默认 RQ 队列（连接到 Redis）。"""
    conn = redis.from_url(settings.REDIS_URL)
    return Queue("default", connection=conn)
