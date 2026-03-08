from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from fastapi import File, HTTPException, Query, UploadFile
from sqlalchemy import func, select

from app.api.schemas import ApiResponse, GoodsCreate, GoodsOut, GoodsSpecCreate, GoodsSpecOut, GoodsSpecUpdate, GoodsUpdate, SpecConfigIn, SpecSkuBindingIn, validate_spec_groups
from app.core.deps import DbSession
from app.domain.models import DeliveryTiming, Goods, GoodsSpec, GoodsXgjPublishShop, SpecSkuBinding

from .common import router
from .xgj_support import apply_goods_xgj_data, load_goods_full, notify_goods_change, sync_goods_to_xgj, sync_xgj_goods


def _raise_goods_read_only() -> None:
    raise HTTPException(status_code=405, detail="商品为云端只读，请使用同步按钮从闲管家拉取数据")


@router.get("/goods")
async def list_goods(
    db: DbSession,
    status: int | None = Query(None, ge=1, le=2),
    goods_type: int | None = Query(None, ge=1, le=3),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ApiResponse:
    from sqlalchemy.orm import selectinload

    stmt = select(Goods).options(
        selectinload(Goods.xgj_profile),
        selectinload(Goods.xgj_properties),
        selectinload(Goods.xgj_publish_shops).selectinload(GoodsXgjPublishShop.images),
        selectinload(Goods.xgj_publish_shops).selectinload(GoodsXgjPublishShop.xgj_shop),
        selectinload(Goods.specs).selectinload(GoodsSpec.sku_bindings),
    ).order_by(Goods.created_at.desc())
    if status is not None:
        stmt = stmt.where(Goods.status == status)
    if goods_type is not None:
        stmt = stmt.where(Goods.goods_type == goods_type)
    result = await db.execute(stmt.limit(limit).offset(offset))
    items = result.scalars().all()

    count_stmt = select(func.count()).select_from(Goods)
    if status is not None:
        count_stmt = count_stmt.where(Goods.status == status)
    if goods_type is not None:
        count_stmt = count_stmt.where(Goods.goods_type == goods_type)
    total = (await db.execute(count_stmt)).scalar_one()
    return ApiResponse(data={
        "total": total,
        "items": [GoodsOut.model_validate(goods).model_dump(mode="json") for goods in items],
    })


@router.post("/goods")
async def create_goods(body: GoodsCreate, db: DbSession) -> ApiResponse:
    _raise_goods_read_only()


@router.get("/goods/{goods_id}")
async def get_goods(goods_id: uuid.UUID, db: DbSession) -> ApiResponse:
    goods = await load_goods_full(db, goods_id)
    return ApiResponse(data=GoodsOut.model_validate(goods).model_dump(mode="json"))


@router.post("/goods/sync")
async def sync_xgj_goods_route(db: DbSession) -> ApiResponse:
    result = await sync_xgj_goods(db)
    return ApiResponse(data=result.model_dump())


@router.patch("/goods/{goods_id}")
async def update_goods(goods_id: uuid.UUID, body: GoodsUpdate, db: DbSession) -> ApiResponse:
    _raise_goods_read_only()


@router.delete("/goods/{goods_id}")
async def delete_goods(goods_id: uuid.UUID, db: DbSession) -> ApiResponse:
    _raise_goods_read_only()


@router.post("/goods/{goods_id}/logo")
async def upload_goods_logo(
    goods_id: uuid.UUID,
    db: DbSession,
    file: UploadFile = File(..., description="商品图片"),
) -> ApiResponse:
    _raise_goods_read_only()


@router.post("/uploads/image")
async def upload_admin_image(file: UploadFile = File(..., description="后台上传图片")) -> ApiResponse:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="文件为空")

    from app.infra.storage import StorageService

    try:
        storage = StorageService()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"存储服务不可用: {exc}")

    source_name = file.filename or "image"
    suffix = Path(source_name).suffix or ".png"
    safe_stem = Path(source_name).stem.replace(" ", "_") or "image"
    storage_key = f"admin/uploads/{uuid.uuid4().hex}-{safe_stem}{suffix}"
    storage.put_bytes(storage_key, data, file.content_type or "image/png")
    return ApiResponse(data={"url": storage.public_url(storage_key)})


@router.post("/goods/{goods_id}/specs")
async def create_goods_spec(goods_id: uuid.UUID, body: GoodsSpecCreate, db: DbSession) -> ApiResponse:
    _raise_goods_read_only()


@router.patch("/goods/{goods_id}/specs/{spec_id}")
async def update_goods_spec(goods_id: uuid.UUID, spec_id: uuid.UUID, body: GoodsSpecUpdate, db: DbSession) -> ApiResponse:
    _raise_goods_read_only()


@router.delete("/goods/{goods_id}/specs/{spec_id}")
async def delete_goods_spec(goods_id: uuid.UUID, spec_id: uuid.UUID, db: DbSession) -> ApiResponse:
    _raise_goods_read_only()


@router.put("/goods/{goods_id}/specs/{spec_id}/bindings")
async def set_spec_bindings(
    goods_id: uuid.UUID,
    spec_id: uuid.UUID,
    body: list[SpecSkuBindingIn],
    db: DbSession,
) -> ApiResponse:
    _raise_goods_read_only()


@router.put("/goods/{goods_id}/spec-config")
async def set_spec_config(goods_id: uuid.UUID, body: SpecConfigIn, db: DbSession) -> ApiResponse:
    _raise_goods_read_only()