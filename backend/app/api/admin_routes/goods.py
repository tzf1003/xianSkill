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
from .xgj_support import apply_goods_xgj_data, load_goods_full, notify_goods_change, sync_goods_to_xgj


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
    import secrets as _sec
    import time as _t

    goods_no = f"G{int(_t.time())}{_sec.token_hex(2).upper()}"
    if body.spec_groups:
        try:
            validate_spec_groups(body.spec_groups)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
    goods = Goods(
        goods_no=goods_no,
        goods_type=body.goods_type,
        goods_name=body.goods_name,
        logo_url=body.logo_url,
        price_cents=body.price_cents,
        stock=body.stock,
        status=body.status,
        multi_spec=body.multi_spec,
        spec_groups=body.spec_groups,
        template=body.template,
        description=body.description,
    )
    db.add(goods)
    await db.flush()
    await apply_goods_xgj_data(db, goods, body, partial=False)

    for spec_in in body.specs:
        spec = GoodsSpec(
            goods_id=goods.id,
            spec_name=spec_in.spec_name,
            price_cents=spec_in.price_cents,
            stock=spec_in.stock,
            enabled=spec_in.enabled,
            xgj_sku_text=spec_in.xgj_sku_text,
            xgj_outer_id=spec_in.xgj_outer_id,
        )
        db.add(spec)
        await db.flush()
        for binding_in in spec_in.sku_bindings:
            db.add(
                SpecSkuBinding(
                    spec_id=spec.id,
                    timing=DeliveryTiming(binding_in.timing),
                    sku_id=binding_in.sku_id,
                )
            )

    await db.flush()
    goods = await sync_goods_to_xgj(db, goods.id)
    await db.commit()
    goods = await load_goods_full(db, goods.id)
    asyncio.create_task(notify_goods_change(goods))
    return ApiResponse(data=GoodsOut.model_validate(goods).model_dump(mode="json"))


@router.get("/goods/{goods_id}")
async def get_goods(goods_id: uuid.UUID, db: DbSession) -> ApiResponse:
    goods = await load_goods_full(db, goods_id)
    return ApiResponse(data=GoodsOut.model_validate(goods).model_dump(mode="json"))


@router.patch("/goods/{goods_id}")
async def update_goods(goods_id: uuid.UUID, body: GoodsUpdate, db: DbSession) -> ApiResponse:
    goods = await load_goods_full(db, goods_id)
    updates = body.model_dump(exclude_unset=True)
    if "spec_groups" in updates and updates["spec_groups"]:
        try:
            validate_spec_groups(updates["spec_groups"])
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
    for field, value in updates.items():
        if field in {"xgj_profile", "xgj_properties", "xgj_publish_shops"}:
            continue
        setattr(goods, field, value)
    await apply_goods_xgj_data(db, goods, body, partial=True)
    await db.flush()
    goods = await sync_goods_to_xgj(db, goods_id)
    await db.commit()
    goods = await load_goods_full(db, goods_id)
    asyncio.create_task(notify_goods_change(goods))
    return ApiResponse(data=GoodsOut.model_validate(goods).model_dump(mode="json"))


@router.delete("/goods/{goods_id}")
async def delete_goods(goods_id: uuid.UUID, db: DbSession) -> ApiResponse:
    goods = await db.get(Goods, goods_id)
    if not goods:
        raise HTTPException(status_code=404, detail="商品不存在")
    await db.delete(goods)
    await db.commit()
    return ApiResponse(data={"deleted": str(goods_id)})


@router.post("/goods/{goods_id}/logo")
async def upload_goods_logo(
    goods_id: uuid.UUID,
    db: DbSession,
    file: UploadFile = File(..., description="商品图片"),
) -> ApiResponse:
    goods = await db.get(Goods, goods_id)
    if not goods:
        raise HTTPException(status_code=404, detail="商品不存在")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="文件为空")

    from app.infra.storage import StorageService

    try:
        storage = StorageService()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"存储服务不可用: {exc}")
    safe_name = (file.filename or "logo").replace(" ", "_")
    storage_key = f"goods/{goods_id}/{safe_name}"
    storage.put_bytes(storage_key, data, file.content_type or "image/png")
    goods.logo_url = storage.public_url(storage_key)
    await db.flush()
    goods = await sync_goods_to_xgj(db, goods_id)
    await db.commit()
    goods = await load_goods_full(db, goods_id)
    asyncio.create_task(notify_goods_change(goods))
    return ApiResponse(data=GoodsOut.model_validate(goods).model_dump(mode="json"))


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
    goods = await db.get(Goods, goods_id)
    if not goods:
        raise HTTPException(status_code=404, detail="商品不存在")
    spec = GoodsSpec(
        goods_id=goods_id,
        spec_name=body.spec_name,
        price_cents=body.price_cents,
        stock=body.stock,
        enabled=body.enabled,
        xgj_sku_text=body.xgj_sku_text,
        xgj_outer_id=body.xgj_outer_id,
    )
    db.add(spec)
    await db.flush()
    for binding_in in body.sku_bindings:
        db.add(
            SpecSkuBinding(
                spec_id=spec.id,
                timing=DeliveryTiming(binding_in.timing),
                sku_id=binding_in.sku_id,
            )
        )
    await db.flush()
    await sync_goods_to_xgj(db, goods_id)
    await db.commit()
    await db.refresh(spec)
    asyncio.create_task(notify_goods_change(goods))
    return ApiResponse(data=GoodsSpecOut.model_validate(spec).model_dump(mode="json"))


@router.patch("/goods/{goods_id}/specs/{spec_id}")
async def update_goods_spec(goods_id: uuid.UUID, spec_id: uuid.UUID, body: GoodsSpecUpdate, db: DbSession) -> ApiResponse:
    spec = await db.get(GoodsSpec, spec_id)
    if not spec or spec.goods_id != goods_id:
        raise HTTPException(status_code=404, detail="规格不存在")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(spec, field, value)
    await db.flush()
    await sync_goods_to_xgj(db, goods_id)
    await db.commit()
    await db.refresh(spec)

    goods = await db.get(Goods, goods_id)
    if goods:
        asyncio.create_task(notify_goods_change(goods))

    return ApiResponse(data=GoodsSpecOut.model_validate(spec).model_dump(mode="json"))


@router.delete("/goods/{goods_id}/specs/{spec_id}")
async def delete_goods_spec(goods_id: uuid.UUID, spec_id: uuid.UUID, db: DbSession) -> ApiResponse:
    spec = await db.get(GoodsSpec, spec_id)
    if not spec or spec.goods_id != goods_id:
        raise HTTPException(status_code=404, detail="规格不存在")
    await db.delete(spec)
    await db.flush()
    await sync_goods_to_xgj(db, goods_id)
    await db.commit()

    goods = await db.get(Goods, goods_id)
    if goods:
        asyncio.create_task(notify_goods_change(goods))

    return ApiResponse(data={"deleted": str(spec_id)})


@router.put("/goods/{goods_id}/specs/{spec_id}/bindings")
async def set_spec_bindings(
    goods_id: uuid.UUID,
    spec_id: uuid.UUID,
    body: list[SpecSkuBindingIn],
    db: DbSession,
) -> ApiResponse:
    spec = await db.get(GoodsSpec, spec_id)
    if not spec or spec.goods_id != goods_id:
        raise HTTPException(status_code=404, detail="规格不存在")
    old_bindings = await db.execute(select(SpecSkuBinding).where(SpecSkuBinding.spec_id == spec_id))
    for binding in old_bindings.scalars().all():
        await db.delete(binding)
    for binding_in in body:
        db.add(
            SpecSkuBinding(
                spec_id=spec_id,
                timing=DeliveryTiming(binding_in.timing),
                sku_id=binding_in.sku_id,
            )
        )
    await db.flush()
    await sync_goods_to_xgj(db, goods_id)
    await db.commit()
    await db.refresh(spec)
    return ApiResponse(data=GoodsSpecOut.model_validate(spec).model_dump(mode="json"))


@router.put("/goods/{goods_id}/spec-config")
async def set_spec_config(goods_id: uuid.UUID, body: SpecConfigIn, db: DbSession) -> ApiResponse:
    goods = await db.get(Goods, goods_id)
    if not goods:
        raise HTTPException(status_code=404, detail="商品不存在")

    try:
        validate_spec_groups(body.spec_groups)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    goods.spec_groups = body.spec_groups
    goods.multi_spec = True

    old_specs = await db.execute(select(GoodsSpec).where(GoodsSpec.goods_id == goods_id))
    for old_spec in old_specs.scalars().all():
        await db.delete(old_spec)
    await db.flush()

    for variant in body.variants:
        spec = GoodsSpec(
            goods_id=goods_id,
            spec_name=variant.spec_name,
            price_cents=variant.price_cents,
            stock=variant.stock,
            enabled=variant.enabled,
            xgj_sku_text=variant.xgj_sku_text,
            xgj_outer_id=variant.xgj_outer_id,
        )
        db.add(spec)
        await db.flush()
        for binding_in in variant.sku_bindings:
            db.add(
                SpecSkuBinding(
                    spec_id=spec.id,
                    timing=DeliveryTiming(binding_in.timing),
                    sku_id=binding_in.sku_id,
                )
            )

    await db.flush()
    await sync_goods_to_xgj(db, goods_id)
    await db.commit()

    asyncio.create_task(notify_goods_change(goods))

    goods = await load_goods_full(db, goods_id)
    return ApiResponse(data=GoodsOut.model_validate(goods).model_dump(mode="json"))