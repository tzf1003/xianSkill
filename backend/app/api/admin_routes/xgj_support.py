from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.schemas import GoodsCreate, GoodsUpdate, XgjShopSyncOut
from app.core.config import settings
from app.core.deps import DbSession
from app.domain.models import (
    Goods,
    GoodsSpec,
    GoodsSubscription,
    GoodsXgjProfile,
    GoodsXgjProperty,
    GoodsXgjPublishShop,
    GoodsXgjPublishShopImage,
    XgjShop,
)
from app.infra.xgj.base_client import XGJApiError
from app.infra.xgj.erp_client import XGJErpClient


async def load_goods_full(db: DbSession, goods_id: uuid.UUID) -> Goods:
    result = await db.execute(
        select(Goods)
        .where(Goods.id == goods_id)
        .options(
            selectinload(Goods.xgj_profile),
            selectinload(Goods.xgj_properties),
            selectinload(Goods.xgj_publish_shops).selectinload(GoodsXgjPublishShop.images),
            selectinload(Goods.xgj_publish_shops).selectinload(GoodsXgjPublishShop.xgj_shop),
            selectinload(Goods.specs).selectinload(GoodsSpec.sku_bindings),
        )
    )
    goods = result.scalar_one_or_none()
    if not goods:
        raise HTTPException(status_code=404, detail="商品不存在")
    return goods


def get_erp_client() -> XGJErpClient:
    return XGJErpClient(app_key=settings.XGJ_ERP_APP_KEY, app_secret=settings.XGJ_ERP_APP_SECRET)


def normalize_xgj_shop_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        shops = payload.get("list")
        if isinstance(shops, list):
            return [item for item in shops if isinstance(item, dict)]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    raise HTTPException(status_code=502, detail="闲管家店铺返回结构异常")


def to_int(value: Any, *, required: bool = False, field_name: str = "") -> int | None:
    if value is None or value == "":
        if required:
            raise HTTPException(status_code=502, detail=f"闲管家店铺字段缺失: {field_name}")
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        if required:
            raise HTTPException(status_code=502, detail=f"闲管家店铺字段格式错误: {field_name}")
        return None


def sync_xgj_shop_entity(shop: XgjShop, data: dict[str, Any]) -> None:
    shop.authorize_expires = to_int(data.get("authorize_expires"), required=True, field_name="authorize_expires") or 0
    shop.user_id = to_int(data.get("user_id"), field_name="user_id")
    shop.user_identity = str(data.get("user_identity") or "")
    shop.user_name = str(data.get("user_name") or "")
    shop.user_nick = str(data.get("user_nick") or "")
    shop.shop_name = str(data.get("shop_name") or "")
    shop.service_support = data.get("service_support") or None
    shop.is_deposit_enough = bool(data.get("is_deposit_enough", False))
    shop.is_pro = bool(data.get("is_pro", False))
    shop.is_valid = bool(data.get("is_valid", False))
    shop.is_trial = bool(data.get("is_trial", False))
    shop.valid_start_time = to_int(data.get("valid_start_time"), field_name="valid_start_time")
    shop.valid_end_time = to_int(data.get("valid_end_time"), required=True, field_name="valid_end_time") or 0
    shop.item_biz_types = str(data.get("item_biz_types") or "")

    missing = [
        name
        for name, value in (
            ("user_identity", shop.user_identity),
            ("user_name", shop.user_name),
            ("user_nick", shop.user_nick),
            ("shop_name", shop.shop_name),
            ("item_biz_types", shop.item_biz_types),
        )
        if not value
    ]
    if missing:
        raise HTTPException(status_code=502, detail=f"闲管家店铺字段缺失: {', '.join(missing)}")


async def sync_xgj_shops(db: DbSession) -> XgjShopSyncOut:
    if not settings.XGJ_ERP_APP_KEY or not settings.XGJ_ERP_APP_SECRET:
        raise HTTPException(status_code=503, detail="未配置闲管家 ERP 凭证")

    try:
        async with get_erp_client() as client:
            payload = await client.get_shops()
    except XGJApiError as exc:
        raise HTTPException(status_code=502, detail=f"同步闲管家店铺失败: {exc.msg}")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"同步闲管家店铺失败: {exc}")

    remote_items = normalize_xgj_shop_list(payload)
    existing_result = await db.execute(select(XgjShop))
    existing_shops = existing_result.scalars().all()
    existing_by_authorize_id = {shop.authorize_id: shop for shop in existing_shops}
    remote_ids: set[int] = set()
    created = 0
    updated = 0

    for item in remote_items:
        authorize_id = to_int(item.get("authorize_id"), required=True, field_name="authorize_id")
        assert authorize_id is not None
        remote_ids.add(authorize_id)
        shop = existing_by_authorize_id.get(authorize_id)
        if shop is None:
            shop = XgjShop(authorize_id=authorize_id)
            db.add(shop)
            created += 1
        else:
            updated += 1
        sync_xgj_shop_entity(shop, item)

    deleted = 0
    for shop in existing_shops:
        if shop.authorize_id not in remote_ids:
            await db.delete(shop)
            deleted += 1

    await db.commit()
    return XgjShopSyncOut(synced=len(remote_items), created=created, updated=updated, deleted=deleted)


def build_xgj_sku_text(goods: Goods, spec: GoodsSpec) -> str:
    if spec.xgj_sku_text:
        return spec.xgj_sku_text
    if not goods.spec_groups:
        return spec.spec_name
    parts = [part.strip() for part in spec.spec_name.split("/")]
    if len(parts) != len(goods.spec_groups):
        return spec.spec_name
    return ";".join(
        f"{group.get('name', '')}:{value}"
        for group, value in zip(goods.spec_groups, parts)
        if group.get("name") and value
    ) or spec.spec_name


def apply_xgj_profile(goods: Goods, profile_data: Any, *, partial: bool) -> None:
    if profile_data is None:
        return

    fields = [
        "item_biz_type",
        "sp_biz_type",
        "category_id",
        "channel_cat_id",
        "original_price_cents",
        "express_fee_cents",
        "stuff_status",
        "notify_url",
        "flash_sale_type",
        "is_tax_included",
    ]
    payload = profile_data.model_dump(exclude_unset=partial)
    profile = goods.xgj_profile
    if profile is None:
        current = {key: payload.get(key) for key in fields}
        missing = [key for key in ("item_biz_type", "sp_biz_type", "channel_cat_id") if not current.get(key)]
        if missing:
            raise HTTPException(status_code=422, detail=f"闲管家配置缺少字段: {', '.join(missing)}")
        goods.xgj_profile = GoodsXgjProfile(goods_id=goods.id, **current)
        return

    for key, value in payload.items():
        setattr(profile, key, value)


def replace_xgj_properties(goods: Goods, properties: list[Any]) -> None:
    goods.xgj_properties = [
        GoodsXgjProperty(
            property_id=item.property_id,
            property_name=item.property_name,
            value_id=item.value_id,
            value_name=item.value_name,
            sort_order=item.sort_order if item.sort_order is not None else index,
        )
        for index, item in enumerate(properties)
    ]


async def replace_xgj_publish_shops(db: DbSession, goods: Goods, shops: list[Any]) -> None:
    selected_shop_ids = [shop_in.xgj_shop_id for shop_in in shops if getattr(shop_in, "xgj_shop_id", None)]
    if len(selected_shop_ids) != len(set(selected_shop_ids)):
        raise HTTPException(status_code=422, detail="闲管家发布店铺不能重复选择同一个本地店铺")

    xgj_shops_by_id: dict[uuid.UUID, XgjShop] = {}
    if selected_shop_ids:
        result = await db.execute(select(XgjShop).where(XgjShop.id.in_(selected_shop_ids)))
        xgj_shops_by_id = {shop.id: shop for shop in result.scalars().all()}
        if len(xgj_shops_by_id) != len(selected_shop_ids):
            raise HTTPException(status_code=422, detail="所选本地店铺不存在或已被删除")

    goods.xgj_publish_shops = []
    for shop_index, shop_in in enumerate(shops):
        linked_shop = xgj_shops_by_id.get(shop_in.xgj_shop_id) if getattr(shop_in, "xgj_shop_id", None) else None
        shop = GoodsXgjPublishShop(
            xgj_shop_id=shop_in.xgj_shop_id,
            user_name=shop_in.user_name,
            province=shop_in.province,
            city=shop_in.city,
            district=shop_in.district,
            title=shop_in.title,
            content=shop_in.content,
            white_image_url=shop_in.white_image_url,
            service_support=shop_in.service_support or (linked_shop.service_support if linked_shop else None),
            sort_order=shop_in.sort_order if shop_in.sort_order is not None else shop_index,
            images=[
                GoodsXgjPublishShopImage(
                    image_url=image.image_url,
                    sort_order=image.sort_order if image.sort_order is not None else image_index,
                )
                for image_index, image in enumerate(shop_in.images)
            ],
        )
        if linked_shop is not None:
            shop.user_name = linked_shop.user_name
        goods.xgj_publish_shops.append(shop)


def build_xgj_publish_shops(goods: Goods) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    shops = sorted(goods.xgj_publish_shops, key=lambda item: item.sort_order)
    for shop in shops:
        images = [img.image_url for img in sorted(shop.images, key=lambda item: item.sort_order)]
        if not images and goods.logo_url:
            images = [goods.logo_url]
        if not images:
            raise HTTPException(status_code=422, detail="闲管家发布店铺至少需要1张图片")
        item = {
            "user_name": shop.user_name,
            "province": shop.province,
            "city": shop.city,
            "district": shop.district,
            "title": shop.title,
            "content": shop.content,
            "images": images,
        }
        if shop.white_image_url:
            item["white_images"] = shop.white_image_url
        if shop.service_support:
            item["service_support"] = shop.service_support
        normalized.append(item)
    return normalized


def build_xgj_product_payload(goods: Goods) -> dict[str, Any]:
    if goods.xgj_profile is None:
        raise HTTPException(status_code=422, detail="缺少闲管家商品配置")
    if not goods.xgj_publish_shops:
        raise HTTPException(status_code=422, detail="缺少闲管家发布店铺配置")

    enabled_specs = [spec for spec in goods.specs if spec.enabled]
    price = goods.price_cents
    stock = goods.stock
    if goods.multi_spec and enabled_specs:
        price = min(spec.price_cents for spec in enabled_specs)
        stock = sum(spec.stock for spec in enabled_specs)

    profile = goods.xgj_profile
    payload: dict[str, Any] = {
        "item_biz_type": profile.item_biz_type,
        "sp_biz_type": profile.sp_biz_type,
        "channel_cat_id": profile.channel_cat_id,
        "price": max(1, int(price)),
        "original_price": max(0, int(profile.original_price_cents)),
        "express_fee": max(0, int(profile.express_fee_cents)),
        "stock": max(1, int(stock)),
        "outer_id": goods.goods_no,
        "stuff_status": profile.stuff_status,
        "publish_shop": build_xgj_publish_shops(goods),
    }
    if profile.category_id is not None:
        payload["category_id"] = profile.category_id
    if profile.notify_url:
        payload["notify_url"] = profile.notify_url
    if profile.flash_sale_type is not None:
        payload["flash_sale_type"] = profile.flash_sale_type
    if profile.is_tax_included:
        payload["is_tax_included"] = profile.is_tax_included
    if goods.xgj_properties:
        payload["channel_pv"] = [
            {
                "property_id": item.property_id,
                "property_name": item.property_name,
                "value_id": item.value_id,
                "value_name": item.value_name,
            }
            for item in sorted(goods.xgj_properties, key=lambda prop: prop.sort_order)
        ]

    if goods.multi_spec and enabled_specs:
        payload["sku_items"] = [
            {
                "price": max(1, int(spec.price_cents)),
                "stock": max(0, int(spec.stock)),
                "sku_text": build_xgj_sku_text(goods, spec),
                "outer_id": spec.xgj_outer_id or str(spec.id),
            }
            for spec in enabled_specs
        ]

    if goods.xgj_goods_id:
        try:
            payload["product_id"] = int(goods.xgj_goods_id)
        except (TypeError, ValueError):
            payload["product_id"] = goods.xgj_goods_id
    return payload


async def sync_goods_to_xgj(db: DbSession, goods_id: uuid.UUID) -> Goods:
    goods = await load_goods_full(db, goods_id)
    if not settings.XGJ_ERP_APP_KEY or not settings.XGJ_ERP_APP_SECRET:
        return goods

    payload = build_xgj_product_payload(goods)

    try:
        async with get_erp_client() as client:
            if goods.xgj_goods_id:
                result = await client.edit_product(payload)
            else:
                result = await client.create_product(payload)
                product_id = result.get("product_id") if isinstance(result, dict) else None
                if product_id:
                    goods.xgj_goods_id = str(product_id)
            if goods.xgj_profile and isinstance(result, dict) and result.get("product_status") is not None:
                goods.xgj_profile.product_status = result.get("product_status")
    except XGJApiError as exc:
        raise HTTPException(status_code=502, detail=f"同步闲管家失败: {exc.msg}")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"同步闲管家失败: {exc}")

    return goods


async def apply_goods_xgj_data(db: DbSession, goods: Goods, body: GoodsCreate | GoodsUpdate, *, partial: bool) -> None:
    if getattr(body, "xgj_profile", None) is not None or not partial:
        apply_xgj_profile(goods, body.xgj_profile, partial=partial)
    if not partial or body.xgj_properties is not None:
        replace_xgj_properties(goods, body.xgj_properties or [])
    if not partial or body.xgj_publish_shops is not None:
        await replace_xgj_publish_shops(db, goods, body.xgj_publish_shops or [])


async def notify_goods_change(goods: Goods) -> None:
    try:
        from app.core.database import async_session_factory

        async with async_session_factory() as session:
            result = await session.execute(select(GoodsSubscription).where(GoodsSubscription.goods_id == goods.id))
            subs = result.scalars().all()
            if not subs:
                return
            client = get_virtual_client()
            for sub in subs:
                try:
                    await client.notify_product_change(notify_url=sub.notify_url, goods_no=goods.goods_no)
                except Exception as exc:
                    logging.getLogger(__name__).warning(
                        "商品变更通知失败 goods_no=%s url=%s: %s",
                        goods.goods_no,
                        sub.notify_url,
                        exc,
                    )
    except Exception as exc:
        logging.getLogger(__name__).warning("商品变更通知任务异常: %s", exc)


def get_virtual_client():
    from app.infra.xgj.virtual_client import XGJVirtualClient

    return XGJVirtualClient(
        app_id=settings.XGJ_VIRTUAL_APP_KEY,
        app_secret=settings.XGJ_VIRTUAL_APP_SECRET,
        mch_id=settings.XGJ_VIRTUAL_MCH_ID,
        mch_secret=settings.XGJ_VIRTUAL_MCH_SECRET,
    )