from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """每次请求获取一个数据库会话，结束后自动关闭。"""
    async with async_session_factory() as session:
        yield session


# 可在路由中直接使用的类型别名
DbSession = Annotated[AsyncSession, Depends(get_db)]
