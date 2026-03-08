from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import require_admin

router = APIRouter(
    prefix="/v1/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)