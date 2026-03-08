from __future__ import annotations

import uuid

from fastapi import HTTPException, Query
from sqlalchemy import func, select

from app.api.schemas import ApiResponse, XgjOrderOut
from app.core.deps import DbSession
from app.domain.models import XgjOrder

from .common import router


@router.get("/xgj-orders")
async def list_xgj_orders(
    db: DbSession,
    status: int | None = Query(None),
    goods_no: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ApiResponse:
    stmt = select(XgjOrder).order_by(XgjOrder.created_at.desc())
    if status is not None:
        stmt = stmt.where(XgjOrder.status == status)
    if goods_no:
        stmt = stmt.where(XgjOrder.goods_no == goods_no)
    result = await db.execute(stmt.limit(limit).offset(offset))
    items = result.scalars().all()

    count_stmt = select(func.count()).select_from(XgjOrder)
    if status is not None:
        count_stmt = count_stmt.where(XgjOrder.status == status)
    if goods_no:
        count_stmt = count_stmt.where(XgjOrder.goods_no == goods_no)
    total = (await db.execute(count_stmt)).scalar_one()
    return ApiResponse(data={
        "total": total,
        "items": [XgjOrderOut.model_validate(order).model_dump(mode="json") for order in items],
    })


@router.get("/xgj-orders/{order_id}")
async def get_xgj_order(order_id: uuid.UUID, db: DbSession) -> ApiResponse:
    order = await db.get(XgjOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return ApiResponse(data=XgjOrderOut.model_validate(order).model_dump(mode="json"))