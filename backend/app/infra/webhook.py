"""Webhook 发送 — 带重试与可选 HMAC-SHA256 签名。

安全：签名使用 HMAC-SHA256，密钥存储在数据库 webhooks.secret（不回显）。
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timezone

import httpx

from app.core.url_builder import build_token_url

log = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_DELAYS = [1, 3, 10]  # seconds


def _make_signature(secret: str, body: bytes) -> str:
    """生成 HMAC-SHA256 签名，格式：sha256=<hexdigest>。"""
    mac = hmac.new(secret.encode("utf-8"), body, hashlib.sha256)
    return f"sha256={mac.hexdigest()}"


async def send_webhook(url: str, payload: dict, *, secret: str | None = None) -> bool:
    """向 url 异步 POST payload，失败时重试 _MAX_RETRIES 次。

    Args:
        url: 目标 URL（必须是 http/https）。
        payload: 序列化为 JSON 的事件数据。
        secret: 若提供，则在请求头 X-Signature-SHA256 中携带 HMAC 签名。

    Returns:
        True 表示最终发送成功，False 表示全部重试失败。
    """
    body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
    headers: dict[str, str] = {
        "Content-Type": "application/json; charset=utf-8",
        "X-Event-Time": datetime.now(timezone.utc).isoformat(),
        "X-Delivery-ID": str(uuid.uuid4()),
    }
    if secret:
        headers["X-Signature-SHA256"] = _make_signature(secret, body)

    async with httpx.AsyncClient(timeout=10.0) as client:
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                resp = await client.post(url, content=body, headers=headers)
                if resp.status_code < 300:
                    log.info("webhook ok url=%s attempt=%d status=%d", url, attempt, resp.status_code)
                    return True
                log.warning(
                    "webhook non-2xx url=%s status=%d attempt=%d", url, resp.status_code, attempt
                )
            except Exception as exc:
                log.warning("webhook error url=%s error=%s attempt=%d", url, exc, attempt)

            if attempt < _MAX_RETRIES:
                await asyncio.sleep(_RETRY_DELAYS[attempt - 1])

    log.error("webhook failed after %d attempts url=%s", _MAX_RETRIES, url)
    return False


async def fire_order_paid(
    db_session,
    *,
    order,
    token,
    sku,
    skill,
    base_url: str,
) -> None:
    """查询数据库中所有启用的 webhook，向其发送 order.paid 事件。

    在 create_order 提交事务后以后台任务调用，不阻塞 HTTP 响应。
    """
    from sqlalchemy import select
    from app.domain.models import Webhook

    result = await db_session.execute(select(Webhook).where(Webhook.enabled.is_(True)))
    webhooks = result.scalars().all()
    if not webhooks:
        return

    token_url = build_token_url(token.token)
    payload = {
        "event": "order.paid",
        "order_id": str(order.id),
        "token_url": token_url,
        "sku": {
            "id": str(sku.id),
            "name": sku.name,
            "delivery_mode": sku.delivery_mode.value,
            "human_sla_hours": sku.human_sla_hours,
        },
        "skill": {
            "id": str(skill.id),
            "name": skill.name,
            "type": skill.type.value,
        },
    }

    tasks = [
        send_webhook(wh.url, payload, secret=wh.secret)
        for wh in webhooks
        if wh.events is None or "order.paid" in (wh.events or [])
    ]
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
