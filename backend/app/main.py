from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.admin import router as admin_router
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
app.include_router(admin_router)

