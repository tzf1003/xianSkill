from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from rq import Queue
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.infra.queue import get_queue as _get_queue
from app.infra.storage import StorageService, get_storage as _get_storage


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """每次请求获取一个数据库会话，结束后自动关闭。"""
    async with async_session_factory() as session:
        yield session


def get_queue() -> Queue:
    """返回 RQ 队列（可在测试中覆盖）。"""
    return _get_queue()


def get_storage() -> StorageService:
    """返回 MinIO 存储服务（可在测试中覆盖）。"""
    return _get_storage()


# 可在路由中直接使用的类型别名
DbSession = Annotated[AsyncSession, Depends(get_db)]

