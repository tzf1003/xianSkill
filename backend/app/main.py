from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

# Python 3.13 on Windows: ProactorEventLoop 与 Docker port-forwarding 不兼容，
# 切换为 SelectorEventLoop 修复 asyncpg/asyncio 连接问题
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI

from app.api.admin import auth_router, router as admin_router
from app.api.health import router as health_router
from app.api.public import router as public_router
from app.core.config import settings
from app.core.database import close_db, init_db
from app.infra.storage import StorageService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # 确保 MinIO bucket 存在
    try:
        StorageService().ensure_bucket()
        logger.info("MinIO bucket '%s' ready.", settings.MINIO_BUCKET)
    except Exception as exc:
        logger.warning("MinIO not available at startup: %s", exc)
    yield
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(public_router)
app.include_router(auth_router)   # /v1/admin/login（无需鉴权）
app.include_router(admin_router)  # /v1/admin/*（需要 Bearer token）

