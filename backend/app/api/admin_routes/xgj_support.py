from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import HTTPException
import httpx
from sqlalchemy import inspect, select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import NO_VALUE

from app.api.schemas import GoodsCreate, GoodsUpdate, XgjGoodsSyncOut, XgjShopSyncOut
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

logger = logging.getLogger(__name__)


async def fetch_xgj_sku_items(client: XGJErpClient, product_id: int) -> tuple[list[dict[str, Any]], bool]:
    try:
        payload = await client.get_product_sku([product_id])
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {400, 404}:
            logger.warning(
                "闲管家商品 SKU 拉取降级为无规格 product_id=%s status=%s",
                product_id,
                exc.response.status_code,
            )
            return [], True
        raise
    except XGJApiError as exc:
        logger.warning("闲管家商品 SKU 拉取降级为无规格 product_id=%s: %s", product_id, exc.msg)
        return [], True
    return normalize_xgj_sku_list(payload, product_id), False


def normalize_xgj_detail_sku_items(detail: dict[str, Any]) -> list[dict[str, Any]]:
    raw_items = detail.get("sku_items")
    if not isinstance(raw_items, list):
        return []
    return [item for item in raw_items if isinstance(item, dict)]


def get_loaded_relation(entity: Any, name: str, default: Any = None) -> Any:
    value = inspect(entity).attrs[name].loaded_value
    if value is NO_VALUE:
        return default
    return value


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


def normalize_xgj_product_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        items = payload.get("list")
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    raise HTTPException(status_code=502, detail="闲管家商品列表返回结构异常")


def normalize_xgj_product_detail(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    raise HTTPException(status_code=502, detail="闲管家商品详情返回结构异常")


def normalize_xgj_sku_list(payload: Any, product_id: int) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        items = payload.get("list")
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and to_int(item.get("product_id"), field_name="product_id") == product_id:
                    sku_items = item.get("sku_items")
                    if isinstance(sku_items, list):
                        return [sku for sku in sku_items if isinstance(sku, dict)]
                    return []
            return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    raise HTTPException(status_code=502, detail="闲管家商品规格返回结构异常")


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


def normalize_remote_image(value: Any) -> str | None:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    if isinstance(value, dict):
        src = value.get("src")
        if isinstance(src, str):
            cleaned = src.strip()
            return cleaned or None
    return None


def extract_image_list(raw_images: Any) -> list[str]:
    if not isinstance(raw_images, list):
        return []
    return [image for item in raw_images if (image := normalize_remote_image(item))]


def extract_goods_logo(detail: dict[str, Any]) -> str | None:
    publish_shop = detail.get("publish_shop")
    if isinstance(publish_shop, list):
        for shop in publish_shop:
            if isinstance(shop, dict):
                images = extract_image_list(shop.get("images"))
                if images:
                    return images[0]
    detail_images = extract_image_list(detail.get("detail_images"))
    if detail_images:
        return detail_images[0]
    return None


def infer_local_goods_type(detail: dict[str, Any]) -> int:
    sp_biz_type = to_int(detail.get("sp_biz_type"), field_name="sp_biz_type")
    if sp_biz_type == 25:
        return 3
    if sp_biz_type in {22, 23}:
        return 2
    return 1


def infer_local_goods_status(detail: dict[str, Any]) -> int:
    product_status = to_int(detail.get("product_status"), field_name="product_status")
    publish_status = to_int(detail.get("publish_status"), field_name="publish_status")
    if product_status == 22 or publish_status == 3:
        return 1
    return 2


def sku_text_to_local_spec_name(sku_text: str) -> str:
    if not sku_text:
        return "默认"
    parts = []
    for segment in sku_text.split(";"):
        name, _, value = segment.partition(":")
        cleaned = (value or name).strip()
        if cleaned:
            parts.append(cleaned)
    return "/".join(parts) or sku_text


def parse_spec_groups_from_skus(sku_items: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    parsed_rows: list[list[tuple[str, str]]] = []
    for sku in sku_items:
        sku_text = str(sku.get("sku_text") or "").strip()
        if not sku_text:
            return None
        row: list[tuple[str, str]] = []
        for segment in sku_text.split(";"):
            name, sep, value = segment.partition(":")
            if not sep:
                return None
            group_name = name.strip()
            group_value = value.strip()
            if not group_name or not group_value:
                return None
            row.append((group_name, group_value))
        parsed_rows.append(row)

    if not parsed_rows:
        return None

    group_count = len(parsed_rows[0])
    if group_count > 2 or any(len(row) != group_count for row in parsed_rows):
        return None

    grouped_values: list[list[str]] = [[] for _ in range(group_count)]
    group_names = [name for name, _ in parsed_rows[0]]
    for row in parsed_rows:
        for index, (group_name, group_value) in enumerate(row):
            if group_name != group_names[index]:
                return None
            if group_value not in grouped_values[index]:
                grouped_values[index].append(group_value)

    return [
        {"name": group_names[index], "values": values}
        for index, values in enumerate(grouped_values)
    ]


def sync_xgj_goods_profile(goods: Goods, detail: dict[str, Any]) -> None:
    profile = get_loaded_relation(goods, "xgj_profile")
    if profile is None:
        profile = GoodsXgjProfile(goods_id=goods.id, item_biz_type=0, sp_biz_type=0, channel_cat_id="")
        goods.xgj_profile = profile

    profile.item_biz_type = to_int(detail.get("item_biz_type"), required=True, field_name="item_biz_type") or 0
    profile.sp_biz_type = to_int(detail.get("sp_biz_type"), required=True, field_name="sp_biz_type") or 0
    profile.category_id = to_int(detail.get("category_id"), field_name="category_id")
    profile.channel_cat_id = str(detail.get("channel_cat_id") or profile.channel_cat_id or "")
    if not profile.channel_cat_id:
        raise HTTPException(status_code=502, detail="闲管家商品字段缺失: channel_cat_id")
    profile.original_price_cents = to_int(detail.get("original_price"), field_name="original_price") or 0
    profile.express_fee_cents = to_int(detail.get("express_fee"), field_name="express_fee") or 0
    profile.stuff_status = to_int(detail.get("stuff_status"), field_name="stuff_status") or 0
    if "notify_url" in detail:
        profile.notify_url = str(detail.get("notify_url") or "").strip() or None
    profile.flash_sale_type = to_int(detail.get("flash_sale_type"), field_name="flash_sale_type")
    if "is_tax_included" in detail:
        profile.is_tax_included = bool(detail.get("is_tax_included"))
    profile.product_status = to_int(detail.get("product_status"), field_name="product_status")
    profile.publish_status = to_int(detail.get("publish_status"), field_name="publish_status")


def sync_xgj_goods_properties(goods: Goods, detail: dict[str, Any]) -> None:
    raw_properties = detail.get("channel_pv")
    if not isinstance(raw_properties, list):
        goods.xgj_properties = []
        return
    properties: list[GoodsXgjProperty] = []
    for index, item in enumerate(raw_properties):
        if not isinstance(item, dict):
            continue
        properties.append(
            GoodsXgjProperty(
                property_id=str(item.get("property_id") or ""),
                property_name=str(item.get("property_name") or ""),
                value_id=str(item.get("value_id") or ""),
                value_name=str(item.get("value_name") or ""),
                sort_order=index,
            )
        )
    goods.xgj_properties = properties


def sync_xgj_goods_publish_shops(goods: Goods, detail: dict[str, Any], xgj_shops_by_username: dict[str, XgjShop]) -> None:
    raw_shops = detail.get("publish_shop")
    if not isinstance(raw_shops, list):
        goods.xgj_publish_shops = []
        return

    publish_shops: list[GoodsXgjPublishShop] = []
    for shop_index, item in enumerate(raw_shops):
        if not isinstance(item, dict):
            continue
        user_name = str(item.get("user_name") or "").strip()
        linked_shop = xgj_shops_by_username.get(user_name)
        images = extract_image_list(item.get("images"))
        publish_shops.append(
            GoodsXgjPublishShop(
                xgj_shop_id=linked_shop.id if linked_shop else None,
                user_name=user_name,
                province=to_int(item.get("province"), field_name="province") or 0,
                city=to_int(item.get("city"), field_name="city") or 0,
                district=to_int(item.get("district"), field_name="district") or 0,
                title=str(item.get("title") or goods.goods_name),
                content=str(item.get("content") or goods.description or ""),
                white_image_url=str(item.get("white_images") or "").strip() or None,
                service_support=str(item.get("service_support") or linked_shop.service_support or "").strip() or None,
                sort_order=shop_index,
                images=[
                    GoodsXgjPublishShopImage(image_url=image_url, sort_order=image_index)
                    for image_index, image_url in enumerate(images)
                ],
            )
        )
    goods.xgj_publish_shops = publish_shops


def sync_xgj_goods_specs(goods: Goods, sku_items: list[dict[str, Any]]) -> None:
    if not sku_items:
        return

    current_specs = list(get_loaded_relation(goods, "specs", []) or [])
    existing_specs_by_xgj_sku_id = {
        spec.xgj_sku_id: spec for spec in current_specs if spec.xgj_sku_id
    }
    existing_specs_by_outer_id = {
        spec.xgj_outer_id: spec for spec in current_specs if spec.xgj_outer_id
    }
    existing_specs_by_sku_text = {
        spec.xgj_sku_text: spec for spec in current_specs if spec.xgj_sku_text
    }
    existing_specs_by_name = {spec.spec_name: spec for spec in current_specs if spec.spec_name}
    next_specs: list[GoodsSpec] = []

    for sku in sku_items:
        xgj_sku_id = str(sku.get("sku_id") or "").strip() or None
        xgj_outer_id = str(sku.get("outer_id") or "").strip() or None
        xgj_sku_text = str(sku.get("sku_text") or "").strip() or None
        local_spec_name = sku_text_to_local_spec_name(xgj_sku_text or "")

        spec = None
        if xgj_sku_id:
            spec = existing_specs_by_xgj_sku_id.get(xgj_sku_id)
        if spec is None and xgj_outer_id:
            spec = existing_specs_by_outer_id.get(xgj_outer_id)
        if spec is None and xgj_sku_text:
            spec = existing_specs_by_sku_text.get(xgj_sku_text)
        if spec is None and local_spec_name:
            spec = existing_specs_by_name.get(local_spec_name)
        if spec is None and not any((xgj_sku_id, xgj_outer_id, xgj_sku_text, local_spec_name)):
            continue
        if spec is None:
            spec = GoodsSpec(goods_id=goods.id, spec_name="默认")
        spec.spec_name = local_spec_name or spec.spec_name
        spec.price_cents = to_int(sku.get("price"), field_name="price") or 0
        spec.stock = to_int(sku.get("stock"), field_name="stock") or 0
        spec.enabled = True
        spec.xgj_sku_id = xgj_sku_id
        spec.xgj_sku_text = xgj_sku_text
        spec.xgj_outer_id = xgj_outer_id
        next_specs.append(spec)
    goods.specs = next_specs


def sync_xgj_goods_entity(
    goods: Goods,
    detail: dict[str, Any],
    sku_items: list[dict[str, Any]],
    xgj_shops_by_username: dict[str, XgjShop],
    *,
    remote_multi_spec: bool,
    sku_sync_degraded: bool,
) -> None:
    goods.goods_name = str(detail.get("title") or goods.goods_name or "")
    if not goods.goods_name:
        raise HTTPException(status_code=502, detail="闲管家商品字段缺失: title")
    goods.logo_url = extract_goods_logo(detail)
    goods.price_cents = to_int(detail.get("price"), field_name="price") or 0
    goods.stock = to_int(detail.get("stock"), field_name="stock") or 0
    goods.status = infer_local_goods_status(detail)
    goods.multi_spec = remote_multi_spec
    if sku_items:
        goods.spec_groups = parse_spec_groups_from_skus(sku_items)
    elif not remote_multi_spec:
        goods.spec_groups = None
    if goods.goods_type not in {1, 2, 3}:
        goods.goods_type = infer_local_goods_type(detail)
    goods.description = next(
        (
            str(shop.get("content") or "").strip()
            for shop in detail.get("publish_shop", [])
            if isinstance(shop, dict) and str(shop.get("content") or "").strip()
        ),
        goods.description,
    )
    sync_xgj_goods_profile(goods, detail)
    sync_xgj_goods_properties(goods, detail)
    sync_xgj_goods_publish_shops(goods, detail, xgj_shops_by_username)
    if sku_items:
        sync_xgj_goods_specs(goods, sku_items)
    elif not remote_multi_spec:
        goods.specs = []
    elif sku_sync_degraded:
        logger.warning("闲管家商品保留多规格标记但未覆盖规格明细 product_id=%s", detail.get("product_id"))


async def sync_xgj_goods(db: DbSession) -> XgjGoodsSyncOut:
    if not settings.XGJ_ERP_APP_KEY or not settings.XGJ_ERP_APP_SECRET:
        raise HTTPException(status_code=503, detail="未配置闲管家 ERP 凭证")

    try:
        async with get_erp_client() as client:
            remote_items: list[dict[str, Any]] = []
            page_no = 1
            page_size = 100
            total_count: int | None = None

            while True:
                payload = await client.get_product_list(page_no=page_no, page_size=page_size)
                page_items = normalize_xgj_product_list(payload)
                if isinstance(payload, dict):
                    total_count = to_int(payload.get("count"), field_name="count") or total_count
                if not page_items:
                    break
                remote_items.extend(page_items)
                if total_count is not None and len(remote_items) >= total_count:
                    break
                if len(page_items) < page_size:
                    break
                page_no += 1

            shops_result = await db.execute(select(XgjShop))
            xgj_shops_by_username = {
                shop.user_name: shop
                for shop in shops_result.scalars().all()
                if shop.user_name
            }

            goods_result = await db.execute(
                select(Goods).options(
                    selectinload(Goods.xgj_profile),
                    selectinload(Goods.xgj_properties),
                    selectinload(Goods.xgj_publish_shops).selectinload(GoodsXgjPublishShop.images),
                    selectinload(Goods.specs).selectinload(GoodsSpec.sku_bindings),
                )
            )
            existing_goods = goods_result.scalars().all()
            goods_by_xgj_id = {goods.xgj_goods_id: goods for goods in existing_goods if goods.xgj_goods_id}
            goods_by_goods_no = {goods.goods_no: goods for goods in existing_goods}

            synced = 0
            created = 0
            updated = 0
            failed = 0

            for item in remote_items:
                product_id = to_int(item.get("product_id"), required=True, field_name="product_id")
                assert product_id is not None
                try:
                    async with db.begin_nested():
                        detail = normalize_xgj_product_detail(await client.get_product_detail(product_id))
                        spec_type = to_int(detail.get("spec_type"), field_name="spec_type") or to_int(item.get("spec_type"), field_name="spec_type") or 1
                        remote_multi_spec = spec_type == 2
                        sku_items: list[dict[str, Any]] = []
                        sku_sync_degraded = False
                        if remote_multi_spec:
                            sku_items = normalize_xgj_detail_sku_items(detail)
                            if not sku_items:
                                sku_items, sku_sync_degraded = await fetch_xgj_sku_items(client, product_id)

                        xgj_goods_id = str(product_id)
                        goods_no = str(detail.get("outer_id") or item.get("outer_id") or f"XGJ-{product_id}").strip()
                        if not goods_no:
                            raise HTTPException(status_code=502, detail=f"闲管家商品缺少 outer_id: product_id={product_id}")

                        goods = goods_by_xgj_id.get(xgj_goods_id) or goods_by_goods_no.get(goods_no)
                        created_now = goods is None
                        if goods is None:
                            goods = Goods(
                                goods_no=goods_no,
                                goods_type=infer_local_goods_type(detail),
                                xgj_goods_id=xgj_goods_id,
                                goods_name="",
                                xgj_properties=[],
                                xgj_publish_shops=[],
                                specs=[],
                            )
                            db.add(goods)
                            await db.flush()
                        else:
                            if goods.goods_no != goods_no:
                                conflict_goods = goods_by_goods_no.get(goods_no)
                                if conflict_goods is not None and conflict_goods.id != goods.id:
                                    raise HTTPException(status_code=409, detail=f"商品编号冲突: {goods_no}")
                                goods_by_goods_no.pop(goods.goods_no, None)
                                goods.goods_no = goods_no
                            goods.xgj_goods_id = xgj_goods_id

                        sync_xgj_goods_entity(
                            goods,
                            detail,
                            sku_items,
                            xgj_shops_by_username,
                            remote_multi_spec=remote_multi_spec,
                            sku_sync_degraded=sku_sync_degraded,
                        )
                        await db.flush()

                    goods_by_xgj_id[xgj_goods_id] = goods
                    goods_by_goods_no[goods.goods_no] = goods
                    synced += 1
                    if created_now:
                        created += 1
                    else:
                        updated += 1
                except HTTPException as exc:
                    failed += 1
                    logger.warning("同步闲管家商品失败 product_id=%s: %s", product_id, exc.detail)
                except XGJApiError as exc:
                    failed += 1
                    logger.warning("同步闲管家商品失败 product_id=%s: %s", product_id, exc.msg)
                except Exception as exc:
                    failed += 1
                    logger.warning("同步闲管家商品失败 product_id=%s: %s", product_id, exc)

    except XGJApiError as exc:
        raise HTTPException(status_code=502, detail=f"同步闲管家商品失败: {exc.msg}")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"同步闲管家商品失败: {exc}")

    await db.commit()
    return XgjGoodsSyncOut(synced=synced, created=created, updated=updated, failed=failed)


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
                    logger.warning(
                        "商品变更通知失败 goods_no=%s url=%s: %s",
                        goods.goods_no,
                        sub.notify_url,
                        exc,
                    )
    except Exception as exc:
        logger.warning("商品变更通知任务异常: %s", exc)


def get_virtual_client():
    from app.infra.xgj.virtual_client import XGJVirtualClient

    return XGJVirtualClient(
        app_id=settings.XGJ_VIRTUAL_APP_KEY,
        app_secret=settings.XGJ_VIRTUAL_APP_SECRET,
        mch_id=settings.XGJ_VIRTUAL_MCH_ID,
        mch_secret=settings.XGJ_VIRTUAL_MCH_SECRET,
    )