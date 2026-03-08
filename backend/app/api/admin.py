"""Admin API 聚合入口。"""

from __future__ import annotations

from app.api.admin_routes import auth_router, router

__all__ = ["auth_router", "router"]