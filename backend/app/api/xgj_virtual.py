"""
闲管家虚拟货源标准接口网关 — 闲管家调用我方的 API 端点。

所有请求由闲管家发起，携带 Query 参数 mch_id、timestamp、sign，
Body 为 JSON。我方需校验签名后返回标准响应 {code, msg, data}。

接口网关地址 = {XGJ_BASE_URL}/xgj/open
"""

from __future__ import annotations

import logging
import time
import uuid as _uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import String, cast, exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.deps import DbSession
from app.core.url_builder import build_token_url
from app.domain.models import (
    DeliveryMode,
    DeliveryTiming,
    Goods,
    GoodsSpec,
    GoodsSubscription,
    Order,
    OrderStatus,
    SKU,
    SpecSkuBinding,
    Token,
    TokenStatus,
    XgjOrder,
    XgjOrderStatus,
)
from app.infra.xgj.virtual_client import XGJVirtualClient
from app.services import token_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/xgj/open", tags=["xgj-virtual"])
_SKU_GOODS_PREFIX = "SKU-"
_DEFAULT_DELIVERY_CONTENT_TEMPLATE = (
    "您的订单编号为：{$订单编号}，您的卡密信息为：{$卡密信息}\n"
    "请在此处点击链接，按照提示操作，即可使用：{$卡密链接}"
)

# ── 工具函数 ──────────────────────────────────────────────────────────


def _get_client() -> XGJVirtualClient:
    return XGJVirtualClient(
        app_id=settings.XGJ_VIRTUAL_APP_KEY,
        app_secret=settings.XGJ_VIRTUAL_APP_SECRET,
        mch_id=settings.XGJ_VIRTUAL_MCH_ID,
        mch_secret=settings.XGJ_VIRTUAL_MCH_SECRET,
    )


def _ok(data: Any = None) -> dict:
    return {"code": 0, "msg": "OK", "data": data if data is not None else {}}


def _err(code: int, msg: str) -> dict:
    return {"code": code, "msg": msg}


def _now_epoch() -> int:
    return int(time.time())


def _to_epoch(dt: datetime | None) -> int:
    if dt is None:
        return _now_epoch()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def _sku_goods_no(sku: SKU) -> str:
    return f"{_SKU_GOODS_PREFIX}{sku.id}"


def _parse_sku_goods_no(goods_no: str) -> _uuid.UUID | None:
    if not goods_no.startswith(_SKU_GOODS_PREFIX):
        return None
    raw = goods_no[len(_SKU_GOODS_PREFIX):].strip()
    try:
        return _uuid.UUID(raw)
    except ValueError:
        return None


def _doc_order_status(status: int) -> int:
    if status == XgjOrderStatus.success.value:
        return 20
    if status in {XgjOrderStatus.failed.value, XgjOrderStatus.refunded.value}:
        return 30
    return 10


def _render_delivery_content(
    *,
    template: str | None,
    order_no: str,
    goods_name: str,
    token_value: str,
    token_url: str,
    local_order: Order,
    sku: SKU,
) -> str:
    rendered = (template or "").strip() or _DEFAULT_DELIVERY_CONTENT_TEMPLATE
    replacements = {
        "{$订单编号}": order_no,
        "{$卡密信息}": token_value,
        "{$卡密链接}": token_url,
        "{$商品名称}": goods_name,
        "{$SKU名称}": sku.name,
        "{$本地订单编号}": str(local_order.id),
    }
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    return rendered


def _build_card_items(token_value: str, delivery_content: str) -> list[dict[str, Any]]:
    return [{"card_pwd": delivery_content}]


def _build_ticket_items(token_value: str, delivery_content: str, goods_name: str) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    valid_end = now + timedelta(days=365)
    return [
        {
            "code_no": token_value,
            "code_pwd": delivery_content,
            "code_name": goods_name,
            "code_type": 1,
            "valid_start_time": _to_epoch(now),
            "valid_end_time": _to_epoch(valid_end),
            "use_time": 0,
            "revoke_time": 0,
            "status": 1,
        }
    ]


def _build_delivery_info(
    *,
    order_no: str,
    goods_type: int,
    goods_name: str,
    token: Token,
    local_order: Order,
    sku: SKU,
) -> dict[str, Any]:
    token_url = build_token_url(token.token)
    delivery_content = _render_delivery_content(
        template=sku.delivery_content_template,
        order_no=order_no,
        goods_name=goods_name,
        token_value=token.token,
        token_url=token_url,
        local_order=local_order,
        sku=sku,
    )
    delivery_info: dict[str, Any] = {
        "token": token.token,
        "token_url": token_url,
        "delivery_content": delivery_content,
        "local_order_id": str(local_order.id),
        "local_token_id": str(token.id),
        "goods_name": goods_name,
    }
    if goods_type == 2:
        delivery_info["card_items"] = _build_card_items(token.token, delivery_content)
    elif goods_type == 3:
        delivery_info["ticket_items"] = _build_ticket_items(token.token, delivery_content, goods_name)
    else:
        delivery_info["remark"] = delivery_content
    return delivery_info


def _build_xgj_order_payload(xgj_order: XgjOrder, goods_name: str) -> dict[str, Any]:
    payload = {
        "order_type": xgj_order.goods_type,
        "order_no": xgj_order.order_no,
        "out_order_no": xgj_order.out_order_no,
        "order_status": _doc_order_status(xgj_order.status),
        "order_amount": xgj_order.total_price_cents,
        "goods_no": xgj_order.goods_no,
        "goods_name": goods_name,
        "buy_quantity": xgj_order.quantity,
        "order_time": _to_epoch(xgj_order.created_at),
    }
    if payload["order_status"] != 10:
        payload["end_time"] = _to_epoch(xgj_order.updated_at or xgj_order.created_at)
    if isinstance(xgj_order.buyer_info, dict) and xgj_order.buyer_info:
        payload["biz_content"] = xgj_order.buyer_info
    if isinstance(xgj_order.delivery_info, dict):
        if xgj_order.delivery_info.get("card_items"):
            payload["card_items"] = xgj_order.delivery_info["card_items"]
        if xgj_order.delivery_info.get("ticket_items"):
            payload["ticket_items"] = xgj_order.delivery_info["ticket_items"]
        if xgj_order.delivery_info.get("remark"):
            payload["remark"] = xgj_order.delivery_info["remark"]
    return payload


def _resolve_order_spec(goods: Goods, body: dict[str, Any]) -> GoodsSpec | None:
    enabled_specs = [spec for spec in goods.specs if spec.enabled]
    product_sku = str(body.get("product_sku") or "").strip()
    if product_sku:
        for spec in enabled_specs:
            if spec.xgj_sku_id == product_sku or spec.xgj_outer_id == product_sku:
                return spec
        return None
    if goods.multi_spec:
        if len(enabled_specs) == 1:
            return enabled_specs[0]
        return None
    if enabled_specs:
        return enabled_specs[0]
    return None


def _resolve_bound_sku(spec: GoodsSpec | None) -> _uuid.UUID | None:
    if spec is None:
        return None
    for binding in spec.sku_bindings:
        if binding.timing == DeliveryTiming.after_payment and binding.sku_id:
            return binding.sku_id
    return None


def _recalculate_goods_stock(goods: Goods) -> None:
    if goods.multi_spec:
        goods.stock = sum(spec.stock for spec in goods.specs if spec.enabled)
    elif goods.specs:
        goods.stock = goods.specs[0].stock


def _normalize_template(template: Any) -> list[dict[str, Any]]:
    if isinstance(template, list):
        normalized: list[dict[str, Any]] = []
        for item in template:
            if not isinstance(item, dict):
                continue
            code = str(item.get("code") or "").strip()
            name = str(item.get("name") or "").strip()
            if not code or not name:
                continue
            normalized.append(
                {
                    "code": code,
                    "name": name,
                    "desc": str(item.get("desc") or "").strip(),
                    "check": int(item.get("check") or 0),
                }
            )
        return normalized

    if isinstance(template, dict):
        normalized = []
        for code, raw_value in template.items():
            if isinstance(raw_value, dict):
                name = str(raw_value.get("name") or code).strip()
                desc = str(raw_value.get("desc") or "").strip()
                check = int(raw_value.get("check") or 0)
            else:
                name = str(raw_value or code).strip()
                desc = ""
                check = 0
            if not code or not name:
                continue
            normalized.append({"code": str(code), "name": name, "desc": desc, "check": check})
        return normalized

    return []


def _apply_goods_keyword_filter(stmt, keyword: str):
    keyword_filter = exists(
        select(1)
        .select_from(GoodsSpec)
        .join(SpecSkuBinding, SpecSkuBinding.spec_id == GoodsSpec.id)
        .join(SKU, SKU.id == SpecSkuBinding.sku_id)
        .where(
            GoodsSpec.goods_id == Goods.id,
            SKU.name.ilike(f"%{keyword}%"),
        )
    )
    return stmt.where(
        (Goods.goods_name.ilike(f"%{keyword}%"))
        | (Goods.goods_no == keyword)
        | (Goods.goods_no.ilike(f"%{keyword}%"))
        | keyword_filter
    )


def _apply_sku_keyword_filter(stmt, keyword: str):
    normalized_keyword = keyword.strip()
    uuid_like = normalized_keyword
    if normalized_keyword.startswith(_SKU_GOODS_PREFIX):
        uuid_like = normalized_keyword[len(_SKU_GOODS_PREFIX):]
    return stmt.where(
        (SKU.name.ilike(f"%{normalized_keyword}%"))
        | (cast(SKU.id, String) == uuid_like)
        | (cast(SKU.id, String).ilike(f"%{uuid_like}%"))
    )


def _sku_to_dict(sku: SKU) -> dict[str, Any]:
    return {
        "goods_no": _sku_goods_no(sku),
        "goods_type": 2,
        "goods_name": sku.name,
        "price": sku.price_cents,
        "stock": 999999,
        "status": 1 if sku.enabled and sku.delivery_mode == DeliveryMode.auto else 2,
        "update_time": _to_epoch(sku.updated_at or sku.created_at),
        "template": [],
    }


async def _get_sku_by_goods_no(db: AsyncSession, goods_no: str) -> SKU | None:
    sku_id = _parse_sku_goods_no(goods_no)
    if not sku_id:
        return None
    return await db.get(SKU, sku_id)


async def _verify(request: Request, mch_id: str, timestamp: int, sign: str) -> dict | None:
    """校验签名，返回 None 表示通过，否则返回错误响应体。"""
    if mch_id != settings.XGJ_VIRTUAL_MCH_ID:
        logger.warning("mch_id 不匹配: 收到=%s 期望=%s", mch_id, settings.XGJ_VIRTUAL_MCH_ID)
        return _err(1000, "商户不存在")
    # 时间戳有效期 5 分钟
    if abs(int(time.time()) - timestamp) > 300:
        return _err(408, "时间戳已超过有效期")
    body_bytes = await request.body()
    body_json = body_bytes.decode("utf-8") if body_bytes else ""
    client = _get_client()
    expected_sign = client.generate_sign(body_json, timestamp)
    if expected_sign != sign:
        logger.warning(
            "签名不匹配: 收到=%s 期望=%s body=%r timestamp=%s mch_id=%s",
            sign, expected_sign, body_json, timestamp, mch_id,
        )
        return _err(401, "签名错误")
    return None


def _goods_to_dict(goods: Goods, specs: list[GoodsSpec] | None = None) -> dict:
    """将 Goods 模型转为闲管家标准商品字典。"""
    spec_list = specs if specs is not None else (goods.specs or [])
    stock = goods.stock
    if goods.multi_spec and spec_list:
        stock = sum(spec.stock for spec in spec_list if spec.enabled)
    return {
        "goods_no": goods.goods_no,
        "goods_type": goods.goods_type,
        "goods_name": goods.goods_name,
        "price": goods.price_cents,
        "stock": stock,
        "status": goods.status,
        "update_time": _to_epoch(goods.updated_at or goods.created_at),
        "template": _normalize_template(goods.template),
    }


# ══════════════════════════════════════════════════════════════════════
# 基础接口
# ══════════════════════════════════════════════════════════════════════

@router.post("/goofish/open/info")
async def platform_info() -> dict:
    """查询平台信息 — 返回应用 ID (整数)。"""
    return _ok({"app_id": int(settings.XGJ_VIRTUAL_APP_KEY)})


@router.post("/goofish/user/info")
async def merchant_info(
    request: Request,
    mch_id: str = Query(...),
    timestamp: int = Query(...),
    sign: str = Query(...),
) -> dict:
    """查询商户信息 — 返回商户余额。"""
    err = await _verify(request, mch_id, timestamp, sign)
    if err:
        return err
    # 自研系统固定返回大于 0 的余额
    return _ok({"balance": 9999900})


# ══════════════════════════════════════════════════════════════════════
# 商品接口
# ══════════════════════════════════════════════════════════════════════

@router.post("/goofish/goods/list")
async def goods_list(
    request: Request,
    db: DbSession,
    mch_id: str = Query(...),
    timestamp: int = Query(...),
    sign: str = Query(...),
) -> dict:
    """查询商品列表。"""
    err = await _verify(request, mch_id, timestamp, sign)
    if err:
        return err
    body = await request.json()
    page = int(body.get("page_no") or body.get("page") or 1)
    page_size = int(body.get("page_size") or 50)
    page = max(1, page)
    page_size = min(100, max(1, page_size))
    offset = (page - 1) * page_size
    keyword = str(body.get("keyword") or "").strip()
    goods_type = body.get("goods_type")

    from sqlalchemy import func

    if goods_type not in (None, "", 2, "2"):
        return _ok({"list": [], "count": 0})

    stmt = select(SKU).where(SKU.enabled.is_(True), SKU.delivery_mode == DeliveryMode.auto)
    if keyword:
        stmt = _apply_sku_keyword_filter(stmt, keyword)
    stmt = stmt.order_by(SKU.created_at.desc())
    result = await db.execute(stmt.limit(page_size).offset(offset))
    sku_items = result.scalars().all()

    count_stmt = select(func.count()).select_from(SKU).where(SKU.enabled.is_(True), SKU.delivery_mode == DeliveryMode.auto)
    if keyword:
        count_stmt = _apply_sku_keyword_filter(count_stmt, keyword)
    total = (await db.execute(count_stmt)).scalar_one()

    return _ok({
        "list": [_sku_to_dict(sku) for sku in sku_items],
        "count": total,
    })


@router.post("/goofish/goods/detail")
async def goods_detail(
    request: Request,
    db: DbSession,
    mch_id: str = Query(...),
    timestamp: int = Query(...),
    sign: str = Query(...),
) -> dict:
    """查询商品详情。"""
    err = await _verify(request, mch_id, timestamp, sign)
    if err:
        return err
    body = await request.json()
    goods_no = body.get("goods_no", "")
    sku = await _get_sku_by_goods_no(db, goods_no)
    if sku and sku.enabled and sku.delivery_mode == DeliveryMode.auto:
        if body.get("goods_type") not in (None, "") and int(body.get("goods_type")) != 2:
            return _err(1100, "商品不存在")
        return _ok(_sku_to_dict(sku))

    result = await db.execute(select(Goods).where(Goods.goods_no == goods_no))
    goods = result.scalar_one_or_none()
    if not goods:
        return _err(1100, "商品不存在")
    if body.get("goods_type") not in (None, "") and int(body.get("goods_type")) != goods.goods_type:
        return _err(1100, "商品不存在")
    return _ok(_goods_to_dict(goods))


@router.post("/goofish/goods/change/subscribe/list")
async def goods_subscribe_list(
    request: Request,
    db: DbSession,
    mch_id: str = Query(...),
    timestamp: int = Query(...),
    sign: str = Query(...),
) -> dict:
    """查询商品订阅列表。"""
    err = await _verify(request, mch_id, timestamp, sign)
    if err:
        return err
    result = await db.execute(select(GoodsSubscription))
    subs = result.scalars().all()
    # 查找关联的 goods_no
    sub_list = []
    for sub in subs:
        goods = await db.get(Goods, sub.goods_id)
        if goods:
            sub_list.append({
                "goods_no": goods.goods_no,
                "notify_url": sub.notify_url,
            })
    return _ok({"list": sub_list, "count": len(sub_list)})


@router.post("/goofish/goods/change/subscribe")
async def goods_subscribe(
    request: Request,
    db: DbSession,
    mch_id: str = Query(...),
    timestamp: int = Query(...),
    sign: str = Query(...),
) -> dict:
    """订阅商品变更通知 — 保存 goods_no 与 notify_url 的对应关系。"""
    err = await _verify(request, mch_id, timestamp, sign)
    if err:
        return err
    body = await request.json()
    goods_no = body.get("goods_no", "")
    notify_url = body.get("notify_url", "")
    if not goods_no or not notify_url:
        return _err(1, "缺少 goods_no 或 notify_url")

    result = await db.execute(select(Goods).where(Goods.goods_no == goods_no))
    goods = result.scalar_one_or_none()
    if not goods:
        return _err(1100, "商品不存在")

    # 避免重复订阅
    existing = await db.execute(
        select(GoodsSubscription).where(
            GoodsSubscription.goods_id == goods.id,
            GoodsSubscription.notify_url == notify_url,
        )
    )
    if existing.scalar_one_or_none():
        return _ok()

    sub = GoodsSubscription(goods_id=goods.id, notify_url=notify_url)
    db.add(sub)
    await db.commit()
    logger.info("XGJ virtual: subscribe goods_no=%s notify_url=%s", goods_no, notify_url)
    return _ok()


@router.post("/goofish/goods/change/unsubscribe")
async def goods_unsubscribe(
    request: Request,
    db: DbSession,
    mch_id: str = Query(...),
    timestamp: int = Query(...),
    sign: str = Query(...),
) -> dict:
    """取消商品变更通知。"""
    err = await _verify(request, mch_id, timestamp, sign)
    if err:
        return err
    body = await request.json()
    goods_no = body.get("goods_no", "")

    result = await db.execute(select(Goods).where(Goods.goods_no == goods_no))
    goods = result.scalar_one_or_none()
    if not goods:
        return _err(1100, "商品不存在")

    # 删除该商品的所有订阅
    subs = await db.execute(
        select(GoodsSubscription).where(GoodsSubscription.goods_id == goods.id)
    )
    for sub in subs.scalars().all():
        await db.delete(sub)
    await db.commit()
    logger.info("XGJ virtual: unsubscribe goods_no=%s", goods_no)
    return _ok()


# ══════════════════════════════════════════════════════════════════════
# 订单接口
# ══════════════════════════════════════════════════════════════════════

async def _create_order(
    db: AsyncSession,
    body: dict,
    goods_type_required: int,
) -> dict:
    """通用下单逻辑。"""
    order_no = body.get("order_no", "")
    goods_no = body.get("goods_no", "")
    try:
        quantity = int(body.get("buy_quantity") or body.get("quantity") or 1)
    except (TypeError, ValueError):
        return _err(1201, "下单参数错误")

    if not order_no or not goods_no:
        return _err(1201, "下单参数错误")

    # 检查订单号是否已存在
    existing = await db.execute(select(XgjOrder).where(XgjOrder.order_no == order_no))
    if existing.scalar_one_or_none():
        return _err(1203, "下单管家订单号已存在")

    sku_goods = await _get_sku_by_goods_no(db, goods_no)
    if sku_goods is not None:
        if goods_type_required != 2:
            return _err(1201, "商品类型不匹配")
        if not sku_goods.enabled or sku_goods.delivery_mode != DeliveryMode.auto:
            return _err(1101, "商品不可用")

        max_amount = body.get("max_amount")
        if max_amount not in (None, ""):
            try:
                max_amount_int = int(max_amount)
            except (TypeError, ValueError):
                return _err(1201, "下单参数错误")
            if sku_goods.price_cents * quantity > max_amount_int:
                return _err(1202, "下单金额低于成本价")

        out_order_no = f"XGJ-{_uuid.uuid4().hex[:16].upper()}"
        local_order = Order(sku_id=sku_goods.id, channel="xgj_virtual")
        db.add(local_order)
        await db.flush()

        token = await token_service.create_token(
            db,
            order_id=local_order.id,
            sku_id=sku_goods.id,
            skill_id=sku_goods.skill_id,
            total_uses=max(1, sku_goods.total_uses * quantity),
        )
        await db.flush()

        delivery_info = _build_delivery_info(
            order_no=order_no,
            goods_type=2,
            goods_name=sku_goods.name,
            token=token,
            local_order=local_order,
            sku=sku_goods,
        )
        delivery_info["virtual_source"] = "sku"
        delivery_info["local_sku_id"] = str(sku_goods.id)

        xgj_order = XgjOrder(
            order_no=order_no,
            out_order_no=out_order_no,
            goods_no=goods_no,
            spec_id=None,
            goods_type=2,
            status=XgjOrderStatus.success.value,
            quantity=quantity,
            total_price_cents=sku_goods.price_cents * quantity,
            buyer_info=body.get("biz_content") or body.get("buyer_info") or body,
            delivery_info=delivery_info,
        )
        db.add(xgj_order)
        await db.commit()
        logger.info("XGJ virtual: sku order created order_no=%s out_order_no=%s sku=%s", order_no, out_order_no, sku_goods.id)
        return _ok(_build_xgj_order_payload(xgj_order, sku_goods.name))

    # 查商品
    result = await db.execute(
        select(Goods)
        .where(Goods.goods_no == goods_no)
        .options(selectinload(Goods.specs).selectinload(GoodsSpec.sku_bindings))
    )
    goods = result.scalar_one_or_none()
    if not goods:
        return _err(1100, "商品不存在")
    if goods.goods_type != goods_type_required:
        return _err(1201, "商品类型不匹配")
    if goods.status != 1:
        return _err(1101, "商品不可用")
    if quantity <= 0:
        return _err(1201, "下单参数错误")

    spec = _resolve_order_spec(goods, body)
    if goods.multi_spec and spec is None:
        return _err(1201, "多规格商品缺少有效规格")

    unit_price = spec.price_cents if spec is not None else goods.price_cents
    available_stock = spec.stock if spec is not None else goods.stock
    if available_stock < quantity:
        return _err(1102, "商品库存不足")

    max_amount = body.get("max_amount")
    if max_amount not in (None, ""):
        try:
            max_amount_int = int(max_amount)
        except (TypeError, ValueError):
            return _err(1201, "下单参数错误")
        if unit_price * quantity > max_amount_int:
            return _err(1202, "下单金额低于成本价")

    bound_sku_id = _resolve_bound_sku(spec)
    if not bound_sku_id:
        return _err(1201, "商品未绑定自动发货SKU")

    sku = await db.get(SKU, bound_sku_id)
    if not sku or not sku.enabled:
        return _err(1201, "绑定的SKU不可用")
    if sku.delivery_mode != DeliveryMode.auto:
        return _err(1201, "绑定的SKU不是自动发货")

    # 生成我方订单号
    out_order_no = f"XGJ-{_uuid.uuid4().hex[:16].upper()}"

    local_order = Order(sku_id=sku.id, channel="xgj_virtual")
    db.add(local_order)
    await db.flush()

    token = await token_service.create_token(
        db,
        order_id=local_order.id,
        sku_id=sku.id,
        skill_id=sku.skill_id,
        total_uses=max(1, sku.total_uses * quantity),
    )
    await db.flush()

    delivery_info = _build_delivery_info(
        order_no=order_no,
        goods_type=goods.goods_type,
        goods_name=goods.goods_name,
        token=token,
        local_order=local_order,
        sku=sku,
    )

    xgj_order = XgjOrder(
        order_no=order_no,
        out_order_no=out_order_no,
        goods_no=goods_no,
        spec_id=spec.id if spec is not None else None,
        goods_type=goods.goods_type,
        status=XgjOrderStatus.success.value,
        quantity=quantity,
        total_price_cents=unit_price * quantity,
        buyer_info=body.get("biz_content") or body.get("buyer_info") or body,
        delivery_info=delivery_info,
    )
    db.add(xgj_order)

    # 扣减库存
    if spec is not None:
        spec.stock -= quantity
    else:
        goods.stock -= quantity
    _recalculate_goods_stock(goods)
    await db.commit()

    logger.info(
        "XGJ virtual: order created order_no=%s out_order_no=%s goods=%s",
        order_no, out_order_no, goods_no,
    )

    return _ok(_build_xgj_order_payload(xgj_order, goods.goods_name))


@router.post("/goofish/order/recharge/create")
async def create_recharge_order(
    request: Request,
    db: DbSession,
    mch_id: str = Query(...),
    timestamp: int = Query(...),
    sign: str = Query(...),
) -> dict:
    """创建直充订单。"""
    err = await _verify(request, mch_id, timestamp, sign)
    if err:
        return err
    body = await request.json()
    return await _create_order(db, body, goods_type_required=1)


@router.post("/goofish/order/purchase/create")
async def create_purchase_order(
    request: Request,
    db: DbSession,
    mch_id: str = Query(...),
    timestamp: int = Query(...),
    sign: str = Query(...),
) -> dict:
    """创建卡密订单。"""
    err = await _verify(request, mch_id, timestamp, sign)
    if err:
        return err
    body = await request.json()
    return await _create_order(db, body, goods_type_required=2)


@router.post("/goofish/order/ticket/create")
async def create_ticket_order(
    request: Request,
    db: DbSession,
    mch_id: str = Query(...),
    timestamp: int = Query(...),
    sign: str = Query(...),
) -> dict:
    """创建券码订单。"""
    err = await _verify(request, mch_id, timestamp, sign)
    if err:
        return err
    body = await request.json()
    return await _create_order(db, body, goods_type_required=3)


@router.post("/goofish/order/detail")
async def order_detail(
    request: Request,
    db: DbSession,
    mch_id: str = Query(...),
    timestamp: int = Query(...),
    sign: str = Query(...),
) -> dict:
    """查询订单详情。"""
    err = await _verify(request, mch_id, timestamp, sign)
    if err:
        return err
    body = await request.json()
    order_no = body.get("order_no") or body.get("out_order_no", "")

    stmt = select(XgjOrder).where(
        (XgjOrder.order_no == order_no) | (XgjOrder.out_order_no == order_no)
    )
    result = await db.execute(stmt)
    xgj_order = result.scalar_one_or_none()
    if not xgj_order:
        return _err(1200, "订单不存在")
    goods_name = xgj_order.goods_no
    if isinstance(xgj_order.delivery_info, dict) and xgj_order.delivery_info.get("goods_name"):
        goods_name = xgj_order.delivery_info["goods_name"]
    else:
        goods_result = await db.execute(select(Goods).where(Goods.goods_no == xgj_order.goods_no))
        goods = goods_result.scalar_one_or_none()
        if goods:
            goods_name = goods.goods_name
    return _ok(_build_xgj_order_payload(xgj_order, goods_name))


# ══════════════════════════════════════════════════════════════════════
# 退款接口
# ══════════════════════════════════════════════════════════════════════

@router.post("/goofish/order/refund/apply")
async def refund_apply(
    request: Request,
    db: DbSession,
    mch_id: str = Query(...),
    timestamp: int = Query(...),
    sign: str = Query(...),
) -> dict:
    """券码订单退款申请 — 二次校验。"""
    err = await _verify(request, mch_id, timestamp, sign)
    if err:
        return err
    body = await request.json()
    order_no = body.get("order_no", "")

    result = await db.execute(select(XgjOrder).where(XgjOrder.order_no == order_no))
    xgj_order = result.scalar_one_or_none()
    if not xgj_order:
        return _err(1200, "订单不存在")

    logger.info(
        "XGJ virtual: refund apply order=%s amount=%s",
        order_no, body.get("refund_amount"),
    )
    return _ok({"result": "agree", "remark": ""})


@router.post("/goofish/order/refund/notify")
async def refund_notify(
    request: Request,
    db: DbSession,
    mch_id: str = Query(...),
    timestamp: int = Query(...),
    sign: str = Query(...),
) -> dict:
    """券码订单退款通知 — 退款成功后更新订单状态。"""
    err = await _verify(request, mch_id, timestamp, sign)
    if err:
        return {"result": "fail", "msg": err["msg"]}
    body = await request.json()
    order_no = body.get("order_no", "")

    result = await db.execute(select(XgjOrder).where(XgjOrder.order_no == order_no))
    xgj_order = result.scalar_one_or_none()
    if xgj_order:
        xgj_order.status = XgjOrderStatus.refunded.value
        if isinstance(xgj_order.delivery_info, dict):
            token_id = xgj_order.delivery_info.get("local_token_id")
            if token_id:
                token = await db.get(Token, _uuid.UUID(str(token_id)))
                if token:
                    token.status = TokenStatus.revoked
            order_id = xgj_order.delivery_info.get("local_order_id")
            if order_id:
                local_order = await db.get(Order, _uuid.UUID(str(order_id)))
                if local_order:
                    local_order.status = OrderStatus.canceled
        if isinstance(xgj_order.delivery_info, dict) and xgj_order.delivery_info.get("virtual_source") == "sku":
            await db.commit()
            logger.info(
                "XGJ virtual: refund notify order=%s amount=%s",
                order_no, body.get("refund_amount"),
            )
            return {"result": "success", "msg": "接收成功"}
        # 恢复库存
        goods_result = await db.execute(
            select(Goods)
            .where(Goods.goods_no == xgj_order.goods_no)
            .options(selectinload(Goods.specs))
        )
        goods = goods_result.scalar_one_or_none()
        if goods:
            if xgj_order.spec_id:
                for spec in goods.specs:
                    if spec.id == xgj_order.spec_id:
                        spec.stock += xgj_order.quantity
                        break
                _recalculate_goods_stock(goods)
            else:
                goods.stock = goods.stock + xgj_order.quantity
        await db.commit()

    logger.info(
        "XGJ virtual: refund notify order=%s amount=%s",
        order_no, body.get("refund_amount"),
    )
    return {"result": "success", "msg": "接收成功"}
