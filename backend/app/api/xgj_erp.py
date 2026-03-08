"""
闲管家进销存（ERP）消息推送接收端点。

闲管家在商品/订单变更时主动推送通知到我方预先注册的 URL。
推送请求携带 Query 参数 appid、timestamp、sign，Body 为 JSON。
需校验签名后返回 {"result": "success/fail", "msg": "..."}.

注册地址：
  商品消息推送URL = {BASE_URL}/xgj/erp/push/product
  订单消息推送URL = {BASE_URL}/xgj/erp/push/order
"""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import APIRouter, Query, Request
from sqlalchemy import or_, select

from app.core.config import settings
from app.core.deps import DbSession
from app.domain.models import DeliveryMode, Order, SKU, Token, XgjOrder
from app.infra.xgj.base_client import XGJBaseClient
from app.services import token_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/xgj/erp", tags=["xgj-erp"])

# ── 签名校验 ──────────────────────────────────────────────────────────


def _verify_erp_sign(body_json: str, appid: str, timestamp: int, sign: str) -> str | None:
    """校验来自闲管家 ERP 平台的推送签名。返回错误信息或 None（通过）。"""
    if str(appid) != str(settings.XGJ_ERP_APP_KEY):
        return "AppKey 不匹配"
    if abs(int(time.time()) - timestamp) > 300:
        return "时间戳已超过有效期"
    # ERP 签名: md5(appKey + "," + md5(body) + "," + timestamp + "," + appSecret)
    body_md5 = XGJBaseClient._md5(body_json)
    raw = f"{settings.XGJ_ERP_APP_KEY},{body_md5},{timestamp},{settings.XGJ_ERP_APP_SECRET}"
    expected = XGJBaseClient._md5(raw)
    if expected != sign:
        return "签名校验失败"
    return None


def _extract_source_order_no(body: dict) -> str:
    return str(body.get("biz_order_no") or body.get("order_no") or body.get("out_order_no") or "").strip()


def _to_uuid(value: object) -> uuid.UUID | None:
    if isinstance(value, uuid.UUID):
        return value
    if isinstance(value, str) and value:
        try:
            return uuid.UUID(value)
        except ValueError:
            return None
    return None


def _build_reward_plan(sku: SKU, quantity: int) -> dict:
    return {
        "reward_sku_id": str(sku.id),
        "reward_sku_name": sku.name,
        "pending_uses": max(1, sku.total_uses * max(1, quantity)),
        "granted_uses": 0,
    }


async def _load_order_context(db, xgj_order: XgjOrder, delivery_info: dict) -> tuple[Order | None, SKU | None]:
    local_order_id = xgj_order.local_order_id or _to_uuid(delivery_info.get("local_order_id"))
    local_order = await db.get(Order, local_order_id) if local_order_id else None
    sku = await db.get(SKU, local_order.sku_id) if local_order else None
    return local_order, sku


async def _find_project_reward_sku(db, *, base_sku: SKU | None, trigger: DeliveryMode) -> SKU | None:
    if base_sku is None or base_sku.project_id is None:
        return None

    stmt = (
        select(SKU)
        .where(
            SKU.project_id == base_sku.project_id,
            SKU.enabled.is_(True),
            SKU.delivery_mode == trigger,
        )
        .order_by(SKU.created_at.asc())
    )
    return (await db.execute(stmt)).scalars().first()


async def _resolve_reward_plan(db, *, xgj_order: XgjOrder, delivery_info: dict, trigger: DeliveryMode) -> tuple[dict | None, Order | None, SKU | None]:
    reward_plans = dict(delivery_info.get("reward_plans") or {})
    reward_plan = reward_plans.get(trigger.value)
    local_order, sku = await _load_order_context(db, xgj_order, delivery_info)

    if reward_plan is None and sku is not None:
        reward_sku: SKU | None = None
        if sku.delivery_mode == trigger:
            reward_sku = sku
        else:
            reward_sku = await _find_project_reward_sku(db, base_sku=sku, trigger=trigger)
        if reward_sku is not None:
            reward_plan = _build_reward_plan(reward_sku, xgj_order.quantity)
            reward_plans[trigger.value] = reward_plan
            delivery_info["reward_plans"] = reward_plans

    return reward_plan, local_order, sku


async def _grant_token_uses_by_source_order(db, *, source_order_no: str, trigger: DeliveryMode) -> tuple[bool, str]:
    if not source_order_no:
        logger.warning("XGJ ERP reward skipped: trigger=%s reason=missing_source_order_no", trigger.value)
        return False, "缺少订单号"

    stmt = select(XgjOrder).where(
        or_(
            XgjOrder.source_order_no == source_order_no,
            XgjOrder.order_no == source_order_no,
            XgjOrder.out_order_no == source_order_no,
        )
    )
    xgj_order = (await db.execute(stmt)).scalars().first()
    if not xgj_order:
        logger.warning(
            "XGJ ERP reward skipped: trigger=%s source_order_no=%s reason=order_not_found",
            trigger.value,
            source_order_no,
        )
        return False, f"未找到关联订单: {source_order_no}"

    delivery_info = dict(xgj_order.delivery_info) if isinstance(xgj_order.delivery_info, dict) else {}
    reward_plan, local_order, sku = await _resolve_reward_plan(db, xgj_order=xgj_order, delivery_info=delivery_info, trigger=trigger)

    if reward_plan is not None:
        pending_uses = int(reward_plan.get("pending_uses") or 0)
        granted_uses = int(reward_plan.get("granted_uses") or 0)
    else:
        expected_trigger = str(delivery_info.get("grant_trigger") or "")
        pending_uses = int(delivery_info.get("pending_reward_uses") or 0)
        if not expected_trigger and sku is not None and sku.delivery_mode in {DeliveryMode.after_receipt, DeliveryMode.after_review}:
            expected_trigger = sku.delivery_mode.value
            delivery_info["grant_trigger"] = expected_trigger
        if pending_uses <= 0 and sku is not None and sku.delivery_mode in {DeliveryMode.after_receipt, DeliveryMode.after_review}:
            pending_uses = max(1, sku.total_uses * max(1, xgj_order.quantity))
            delivery_info["pending_reward_uses"] = pending_uses
        if expected_trigger != trigger.value:
            logger.warning(
                "XGJ ERP reward skipped: trigger=%s source_order_no=%s expected_trigger=%s reason=trigger_mismatch",
                trigger.value,
                source_order_no,
                expected_trigger or "unknown",
            )
            return True, f"该订单无需当前回调赠送，当前模式={expected_trigger or 'unknown'}"
        granted_uses = int(delivery_info.get("granted_reward_uses") or 0)

    delta_uses = pending_uses - granted_uses
    if delta_uses <= 0:
        logger.info(
            "XGJ ERP reward ignored: trigger=%s source_order_no=%s pending_uses=%s granted_uses=%s reason=already_granted",
            trigger.value,
            source_order_no,
            pending_uses,
            granted_uses,
        )
        return True, "赠送次数已处理"

    token_id = xgj_order.local_token_id or delivery_info.get("local_token_id")
    token_id = _to_uuid(token_id)
    if not token_id:
        logger.error(
            "XGJ ERP reward failed: trigger=%s source_order_no=%s reason=missing_token_binding",
            trigger.value,
            source_order_no,
        )
        return False, "订单未绑定 token"

    token = await db.get(Token, token_id)
    if not token:
        logger.error(
            "XGJ ERP reward failed: trigger=%s source_order_no=%s token_id=%s reason=token_not_found",
            trigger.value,
            source_order_no,
            token_id,
        )
        return False, "关联 token 不存在"

    token_service.grant_uses(token, delta_uses)
    if reward_plan is not None:
        reward_plan["granted_uses"] = pending_uses
        reward_plans = dict(delivery_info.get("reward_plans") or {})
        reward_plans[trigger.value] = reward_plan
        delivery_info["reward_plans"] = reward_plans
        delivery_info["grant_trigger"] = trigger.value
        delivery_info["pending_reward_uses"] = pending_uses
        delivery_info["granted_reward_uses"] = pending_uses
    else:
        delivery_info["granted_reward_uses"] = pending_uses
    delivery_info["last_reward_event"] = trigger.value
    xgj_order.delivery_info = dict(delivery_info)
    if xgj_order.source_order_no is None:
        xgj_order.source_order_no = source_order_no
    if xgj_order.local_order_id is None and local_order is not None:
        xgj_order.local_order_id = local_order.id
    if xgj_order.local_token_id is None:
        xgj_order.local_token_id = token.id
    await db.commit()
    logger.info(
        "XGJ ERP reward grant: source_order_no=%s trigger=%s uses=%s token=%s reward=%s",
        source_order_no,
        trigger.value,
        delta_uses,
        token.id,
        (reward_plan or {}).get("reward_sku_name") or (sku.name if sku is not None else "legacy"),
    )
    return True, f"已赠送 {delta_uses} 次"


async def _handle_reward_push(db, body: dict, *, trigger: DeliveryMode) -> dict:
    source_order_no = _extract_source_order_no(body)
    ok, msg = await _grant_token_uses_by_source_order(db, source_order_no=source_order_no, trigger=trigger)
    return {"result": "success" if ok else "fail", "msg": msg}


# ══════════════════════════════════════════════════════════════════════
# 商品推送通知
# ══════════════════════════════════════════════════════════════════════

@router.post("/push/product")
async def product_push(
    request: Request,
    appid: str = Query(...),
    timestamp: int = Query(...),
    sign: str = Query(...),
) -> dict:
    """
    商品推送通知 — 商品信息变更时闲管家主动推送。

    Body 字段:
      seller_id, product_id, product_status, publish_status,
      item_biz_type, price, stock, user_name, modify_time
    """
    body_bytes = await request.body()
    body_json = body_bytes.decode("utf-8") if body_bytes else "{}"
    err = _verify_erp_sign(body_json, appid, timestamp, sign)
    if err:
        logger.warning("XGJ ERP product push sign failed: %s", err)
        return {"result": "fail", "msg": err}

    body = await request.json()
    logger.info(
        "XGJ ERP product push: product_id=%s status=%s price=%s stock=%s",
        body.get("product_id"),
        body.get("product_status"),
        body.get("price"),
        body.get("stock"),
    )
    # TODO: 处理商品变更业务逻辑（异步）
    return {"result": "success", "msg": "接收成功"}


# ══════════════════════════════════════════════════════════════════════
# 订单推送通知
# ══════════════════════════════════════════════════════════════════════

@router.post("/push/order")
async def order_push(
    request: Request,
    db: DbSession,
    appid: str = Query(...),
    timestamp: int = Query(...),
    sign: str = Query(...),
) -> dict:
    """
    订单推送通知 — 订单信息/状态/退款发生变更时闲管家主动推送。

    Body 字段:
      seller_id, user_name, order_no, order_type, order_status,
      refund_status, modify_time, product_id, item_id
    """
    body_bytes = await request.body()
    body_json = body_bytes.decode("utf-8") if body_bytes else "{}"
    err = _verify_erp_sign(body_json, appid, timestamp, sign)
    if err:
        logger.warning("XGJ ERP order push sign failed: %s", err)
        return {"result": "fail", "msg": err}

    body = await request.json()
    logger.info(
        "XGJ ERP order push: order_no=%s type=%s status=%s refund=%s",
        body.get("order_no"),
        body.get("order_type"),
        body.get("order_status"),
        body.get("refund_status"),
    )
    if int(body.get("order_status") or 0) == 22:
        ok, msg = await _grant_token_uses_by_source_order(
            db,
            source_order_no=_extract_source_order_no(body),
            trigger=DeliveryMode.after_receipt,
        )
        if ok and msg.startswith("已赠送"):
            logger.info("XGJ ERP order reward granted: source_order_no=%s result=%s", _extract_source_order_no(body), msg)
        else:
            logger.warning("XGJ ERP order reward skipped: source_order_no=%s result=%s", _extract_source_order_no(body), msg)
        if ok and msg.startswith("已赠送"):
            return {"result": "success", "msg": msg}
    return {"result": "success", "msg": "接收成功"}


@router.post("/push/order/receipt")
async def order_receipt_push(
    request: Request,
    db: DbSession,
    appid: str = Query(...),
    timestamp: int = Query(...),
    sign: str = Query(...),
) -> dict:
    body_bytes = await request.body()
    body_json = body_bytes.decode("utf-8") if body_bytes else "{}"
    err = _verify_erp_sign(body_json, appid, timestamp, sign)
    if err:
        logger.warning("XGJ ERP receipt push sign failed: %s", err)
        return {"result": "fail", "msg": err}

    body = await request.json()
    result = await _handle_reward_push(db, body, trigger=DeliveryMode.after_receipt)
    if result.get("result") == "success" and str(result.get("msg") or "").startswith("已赠送"):
        logger.info("XGJ ERP receipt reward granted: source_order_no=%s result=%s", _extract_source_order_no(body), result.get("msg"))
    else:
        logger.warning("XGJ ERP receipt reward skipped: source_order_no=%s result=%s", _extract_source_order_no(body), result.get("msg"))
    return result


@router.post("/push/order/review")
async def order_review_push(
    request: Request,
    db: DbSession,
    appid: str = Query(...),
    timestamp: int = Query(...),
    sign: str = Query(...),
) -> dict:
    body_bytes = await request.body()
    body_json = body_bytes.decode("utf-8") if body_bytes else "{}"
    err = _verify_erp_sign(body_json, appid, timestamp, sign)
    if err:
        logger.warning("XGJ ERP review push sign failed: %s", err)
        return {"result": "fail", "msg": err}

    body = await request.json()
    result = await _handle_reward_push(db, body, trigger=DeliveryMode.after_review)
    if result.get("result") == "success" and str(result.get("msg") or "").startswith("已赠送"):
        logger.info("XGJ ERP review reward granted: source_order_no=%s result=%s", _extract_source_order_no(body), result.get("msg"))
    else:
        logger.warning("XGJ ERP review reward skipped: source_order_no=%s result=%s", _extract_source_order_no(body), result.get("msg"))
    return result
