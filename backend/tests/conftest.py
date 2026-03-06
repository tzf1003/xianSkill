"""测试用 conftest — 使用 SQLite 异步引擎，不依赖外部 Postgres。"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.domain.models import Base

# SQLite async (aiosqlite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """每个测试前创建表，测试后销毁。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """使用测试数据库的 AsyncClient（mock queue 和 storage）。"""
    from app.core import deps
    from app.main import app

    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    class DummyQueue:
        """不入队、不连接 Redis。"""
        def enqueue(self, *args, **kwargs):
            return None

    class MockStorage:
        """内存存储，无需 MinIO。"""
        def __init__(self):
            self._data: dict[str, bytes] = {}

        def ensure_bucket(self): pass

        def put_bytes(self, key, data, content_type="application/octet-stream"):
            self._data[key] = data

        def get_bytes(self, key) -> bytes:
            return self._data.get(key, b"")

        def presigned_get_url(self, key, expires_seconds=3600) -> str:
            return f"http://mock-storage/{key}"

        def presigned_put_url(self, key, expires_seconds=3600) -> str:
            return f"http://mock-storage-put/{key}"

    app.dependency_overrides[deps.get_db] = override_get_db
    app.dependency_overrides[deps.get_queue] = lambda: DummyQueue()
    app.dependency_overrides[deps.get_storage] = lambda: MockStorage()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


    app.dependency_overrides.clear()
