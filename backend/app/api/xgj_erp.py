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

from fastapi import APIRouter, Query, Request

from app.core.config import settings
from app.infra.xgj.base_client import XGJBaseClient

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
    # TODO: 处理订单变更业务逻辑（异步）
    return {"result": "success", "msg": "接收成功"}
