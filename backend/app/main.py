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
from app.api.xgj_erp import router as xgj_erp_router
from app.api.xgj_virtual import router as xgj_virtual_router
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

    # ── 闲管家虚拟货源接口网关 ──
    xgj_base = settings.XGJ_BASE_URL or settings.BASE_URL
    print("═" * 60)
    print("闲管家 · 虚拟货源")
    print(f"  接口网关:      {xgj_base}/xgj/open")
    print(f"  AppKey:        {settings.XGJ_VIRTUAL_APP_KEY}")
    print(f"  AppSecret:     {settings.XGJ_VIRTUAL_APP_SECRET}")
    if settings.XGJ_VIRTUAL_MCH_ID:
        print(f"  商户ID(mch):   {settings.XGJ_VIRTUAL_MCH_ID}")
    else:
        print("  ⚠ 未配置 XGJ_VIRTUAL_MCH_ID（需在 .env 中设置）")
    print("═" * 60)

    # ── 闲管家进销存消息推送 URL ──
    print("闲管家 · 进销存 (ERP)")
    print(f"  AppKey:        {settings.XGJ_ERP_APP_KEY}")
    print(f"  商品消息推送URL: {xgj_base}/xgj/erp/push/product")
    print(f"  订单消息推送URL: {xgj_base}/xgj/erp/push/order")
    print("═" * 60)

    yield
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(public_router)
app.include_router(auth_router)        # /v1/admin/login（无需鉴权）
app.include_router(admin_router)       # /v1/admin/*（需要 Bearer token）
app.include_router(xgj_virtual_router) # /xgj/open/*（闲管家虚拟货源网关）
app.include_router(xgj_erp_router)     # /xgj/erp/*（闲管家进销存推送）

