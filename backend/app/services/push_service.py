from __future__ import annotations

import json
import logging
from urllib.parse import quote

import httpx

from app.domain.models import PushChannel, SKU, XgjOrder

logger = logging.getLogger(__name__)

HUMAN_PUSH_TITLE = "需要人工处理"
_BARK_TIMEOUT_SECONDS = 15.0


def build_human_order_message(
    *,
    sku: SKU,
    job_id: str,
    token_value: str,
    local_order_id: str,
    source_order_no: str | None,
    buyer_info: dict | None,
    inputs: dict | None,
) -> str:
    lines = [
        f"SKU：{sku.name}",
        f"任务ID：{job_id}",
        f"Token：{token_value}",
        f"本地订单ID：{local_order_id}",
    ]
    if source_order_no:
        lines.append(f"闲管家订单号：{source_order_no}")
    if buyer_info:
        lines.append("买家信息：")
        lines.append(json.dumps(buyer_info, ensure_ascii=False, indent=2, sort_keys=True))
    if inputs:
        lines.append("提交参数：")
        lines.append(json.dumps(inputs, ensure_ascii=False, indent=2, sort_keys=True))
    return "\n".join(lines)


def build_human_order_message_from_erp(
    *,
    sku: SKU,
    token_value: str,
    local_order_id: str,
    source_order_no: str | None,
    buyer_info: dict | None,
    erp_payload: dict | None,
) -> str:
    lines = [
        f"SKU：{sku.name}",
        f"Token：{token_value}",
        f"本地订单ID：{local_order_id}",
    ]
    if source_order_no:
        lines.append(f"闲管家订单号：{source_order_no}")
    if buyer_info:
        lines.append("买家信息：")
        lines.append(json.dumps(buyer_info, ensure_ascii=False, indent=2, sort_keys=True))
    if erp_payload:
        lines.append("ERP回调：")
        lines.append(json.dumps(erp_payload, ensure_ascii=False, indent=2, sort_keys=True))
    return "\n".join(lines)


def extract_xgj_notify_url(xgj_order: XgjOrder | None) -> str | None:
    if xgj_order is None or not isinstance(xgj_order.buyer_info, dict):
        return None
    return str(xgj_order.buyer_info.get("notify_url") or "").strip() or None


async def send_push_message(channel: PushChannel, *, title: str, body: str) -> dict:
    provider = (channel.provider or "").strip().lower()
    if provider != "bark":
        raise ValueError(f"Unsupported push provider: {channel.provider}")
    return await _send_bark_message(channel.base_url, title=title, body=body)


async def _send_bark_message(base_url: str, *, title: str, body: str) -> dict:
    raw = (base_url or "").strip()
    if not raw:
        raise ValueError("Bark BASEURL 不能为空")

    async with httpx.AsyncClient(timeout=_BARK_TIMEOUT_SECONDS) as client:
        if raw.rstrip("/").endswith("/push"):
            response = await client.post(raw, json={"title": title, "body": body})
        else:
            normalized = raw.rstrip("/")
            response = await client.get(f"{normalized}/{quote(title, safe='')}/{quote(body, safe='')}")
        response.raise_for_status()
        payload = response.json()

    if isinstance(payload, dict) and int(payload.get("code", 200)) not in {0, 200}:
        logger.warning("Bark push returned non-success payload: %s", payload)
        raise ValueError(str(payload.get("message") or payload.get("msg") or "Bark 推送失败"))
    return payload if isinstance(payload, dict) else {"result": payload}