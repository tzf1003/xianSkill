from __future__ import annotations

from fastapi import Query
from sqlalchemy import func, select

from app.api.schemas import ApiResponse, XgjShopOut
from app.core.deps import DbSession
from app.domain.models import XgjShop

from .common import router
from .xgj_support import sync_xgj_shops


@router.get("/shops")
async def list_xgj_shops(
    db: DbSession,
    valid_only: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ApiResponse:
    stmt = select(XgjShop).order_by(XgjShop.is_valid.desc(), XgjShop.updated_at.desc())
    count_stmt = select(func.count()).select_from(XgjShop)
    if valid_only is not None:
        stmt = stmt.where(XgjShop.is_valid == valid_only)
        count_stmt = count_stmt.where(XgjShop.is_valid == valid_only)
    result = await db.execute(stmt.limit(limit).offset(offset))
    items = result.scalars().all()
    total = (await db.execute(count_stmt)).scalar_one()
    return ApiResponse(data={
        "total": total,
        "items": [XgjShopOut.model_validate(shop).model_dump(mode="json") for shop in items],
    })


@router.post("/shops/sync")
async def sync_xgj_shops_route(db: DbSession) -> ApiResponse:
    result = await sync_xgj_shops(db)
    return ApiResponse(data=result.model_dump())