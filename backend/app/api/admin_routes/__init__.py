from __future__ import annotations

from . import catalog, dashboard, goods, operations, shops, xgj_orders
from .auth import auth_router
from .common import router

__all__ = ["auth_router", "router", "catalog", "dashboard", "goods", "operations", "shops", "xgj_orders"]