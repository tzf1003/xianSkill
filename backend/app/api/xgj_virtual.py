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
from typing import Any

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import DbSession
from app.domain.models import (
    Goods,
    GoodsSpec,
    GoodsSubscription,
    SpecSkuBinding,
    XgjOrder,
    XgjOrderStatus,
)
from app.infra.xgj.virtual_client import XGJVirtualClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/xgj/open", tags=["xgj-virtual"])

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
    return {
        "goods_no": goods.goods_no,
        "goods_type": goods.goods_type,
        "goods_name": goods.goods_name,
        "logo_url": goods.logo_url or "",
        "price": goods.price_cents,
        "stock": goods.stock,
        "status": goods.status,
        "template": goods.template or {},
        "specs": [
            {
                "spec_id": str(s.id),
                "spec_name": s.spec_name,
                "price": s.price_cents,
                "stock": s.stock,
            }
            for s in spec_list if s.enabled
        ],
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
    page = body.get("page", 1)
    page_size = body.get("page_size", 20)
    offset = (max(1, page) - 1) * page_size

    stmt = select(Goods).where(Goods.status == 1).order_by(Goods.created_at.desc())
    result = await db.execute(stmt.limit(page_size).offset(offset))
    goods_list_items = result.scalars().all()
    from sqlalchemy import func
    total = (await db.execute(select(func.count()).select_from(Goods).where(Goods.status == 1))).scalar_one()

    return _ok({
        "list": [_goods_to_dict(g) for g in goods_list_items],
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
    result = await db.execute(select(Goods).where(Goods.goods_no == goods_no))
    goods = result.scalar_one_or_none()
    if not goods:
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
    quantity = body.get("quantity", 1)

    if not order_no or not goods_no:
        return _err(1201, "下单参数错误")

    # 检查订单号是否已存在
    existing = await db.execute(select(XgjOrder).where(XgjOrder.order_no == order_no))
    if existing.scalar_one_or_none():
        return _err(1203, "下单管家订单号已存在")

    # 查商品
    result = await db.execute(select(Goods).where(Goods.goods_no == goods_no))
    goods = result.scalar_one_or_none()
    if not goods:
        return _err(1100, "商品不存在")
    if goods.status != 1:
        return _err(1101, "商品不可用")
    if goods.stock < quantity:
        return _err(1102, "商品库存不足")

    # 生成我方订单号
    out_order_no = f"XGJ-{_uuid.uuid4().hex[:16].upper()}"

    xgj_order = XgjOrder(
        order_no=order_no,
        out_order_no=out_order_no,
        goods_no=goods_no,
        goods_type=goods.goods_type,
        status=XgjOrderStatus.processing.value,
        quantity=quantity,
        total_price_cents=goods.price_cents * quantity,
        buyer_info=body.get("buyer_info") or body.get("account") or body,
    )
    db.add(xgj_order)

    # 扣减库存
    goods.stock = goods.stock - quantity
    await db.commit()

    logger.info(
        "XGJ virtual: order created order_no=%s out_order_no=%s goods=%s",
        order_no, out_order_no, goods_no,
    )

    return _ok({
        "order_no": order_no,
        "out_order_no": out_order_no,
        "status": XgjOrderStatus.processing.value,
    })


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
    return _ok({
        "order_no": xgj_order.order_no,
        "out_order_no": xgj_order.out_order_no,
        "goods_no": xgj_order.goods_no,
        "goods_type": xgj_order.goods_type,
        "status": xgj_order.status,
        "quantity": xgj_order.quantity,
        "total_price": xgj_order.total_price_cents,
        "delivery_info": xgj_order.delivery_info or {},
    })


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
        # 恢复库存
        goods_result = await db.execute(select(Goods).where(Goods.goods_no == xgj_order.goods_no))
        goods = goods_result.scalar_one_or_none()
        if goods:
            goods.stock = goods.stock + xgj_order.quantity
        await db.commit()

    logger.info(
        "XGJ virtual: refund notify order=%s amount=%s",
        order_no, body.get("refund_amount"),
    )
    return {"result": "success", "msg": "接收成功"}
