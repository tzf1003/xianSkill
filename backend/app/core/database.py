from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_recycle=1800,
)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """应用启动时调用。正式环境通过 alembic upgrade head 管理表结构。"""
    # 导入模型以注册到 metadata（Alembic autogenerate 需要）
    import app.domain.models  # noqa: F401


async def close_db() -> None:
    """应用关闭时释放连接池。"""
    await engine.dispose()
