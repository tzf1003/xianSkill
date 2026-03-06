from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """存活探针。"""
    return {"code": 0, "message": "ok", "data": {"status": "healthy"}}
