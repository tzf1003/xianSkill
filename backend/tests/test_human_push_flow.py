from __future__ import annotations

import io
import json
import time

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.domain.models import Token, XgjOrder
from app.infra.xgj.base_client import XGJBaseClient
from app.infra.xgj.virtual_client import XGJVirtualClient


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    resp = await client.post(
        "/v1/admin/login",
        json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['data']['token']}"}


def _virtual_client() -> XGJVirtualClient:
    return XGJVirtualClient(
        app_id=settings.XGJ_VIRTUAL_APP_KEY,
        app_secret=settings.XGJ_VIRTUAL_APP_SECRET,
        mch_id=settings.XGJ_VIRTUAL_MCH_ID,
        mch_secret=settings.XGJ_VIRTUAL_MCH_SECRET,
    )


async def _signed_post(client: AsyncClient, path: str, body: dict):
    body_json = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
    timestamp = int(time.time())
    virtual_client = _virtual_client()
    try:
        sign = virtual_client.generate_sign(body_json, timestamp)
    finally:
        await virtual_client.close()
    return await client.post(
        f"{path}?mch_id={settings.XGJ_VIRTUAL_MCH_ID}&timestamp={timestamp}&sign={sign}",
        content=body_json,
        headers={"Content-Type": "application/json"},
    )


async def _signed_erp_post(client: AsyncClient, path: str, body: dict):
    body_json = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
    timestamp = int(time.time())
    body_md5 = XGJBaseClient._md5(body_json)
    sign = XGJBaseClient._md5(
        f"{settings.XGJ_ERP_APP_KEY},{body_md5},{timestamp},{settings.XGJ_ERP_APP_SECRET}"
    )
    return await client.post(
        f"{path}?appid={settings.XGJ_ERP_APP_KEY}&timestamp={timestamp}&sign={sign}",
        content=body_json,
        headers={"Content-Type": "application/json"},
    )


@pytest.fixture(autouse=True)
def _configure_virtual_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "XGJ_VIRTUAL_APP_KEY", "10001")
    monkeypatch.setattr(settings, "XGJ_VIRTUAL_APP_SECRET", "virtual-app-secret")
    monkeypatch.setattr(settings, "XGJ_VIRTUAL_MCH_ID", "20001")
    monkeypatch.setattr(settings, "XGJ_VIRTUAL_MCH_SECRET", "virtual-mch-secret")
    monkeypatch.setattr(settings, "XGJ_ERP_APP_KEY", "30001")
    monkeypatch.setattr(settings, "XGJ_ERP_APP_SECRET", "erp-app-secret")
    monkeypatch.setattr(settings, "BASE_URL", "http://testserver")
    monkeypatch.setattr(settings, "FRONTEND_BASE_URL", "https://frontend.example.com")


@pytest.mark.asyncio
async def test_push_channel_test_and_human_sku_requires_channel(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    from app.api import admin as admin_api

    push_calls: list[dict] = []

    async def fake_send_push_message(channel, *, title: str, body: str) -> dict:
        push_calls.append({"channel_id": str(channel.id), "title": title, "body": body})
        return {"code": 200, "message": "success"}

    monkeypatch.setattr(admin_api, "send_push_message", fake_send_push_message)

    headers = await _admin_headers(client)
    channel_resp = await client.post(
        "/v1/admin/push-channels",
        json={"name": "Bark 主通道", "provider": "bark", "base_url": "https://api.day.app/device-key"},
        headers=headers,
    )
    assert channel_resp.status_code == 200
    channel_id = channel_resp.json()["data"]["id"]

    test_resp = await client.post(
        f"/v1/admin/push-channels/{channel_id}/test",
        json={"title": "测试标题", "body": "测试推送内容"},
        headers=headers,
    )
    assert test_resp.status_code == 200
    assert push_calls == [{"channel_id": channel_id, "title": "测试标题", "body": "测试推送内容"}]

    skill_resp = await client.post("/v1/admin/skills", json={"name": "人工技能", "type": "prompt"}, headers=headers)
    skill_id = skill_resp.json()["data"]["id"]

    bad_resp = await client.post(
        "/v1/admin/skus",
        json={"skill_id": skill_id, "name": "人工SKU", "delivery_mode": "human", "total_uses": 1},
        headers=headers,
    )
    assert bad_resp.status_code == 400
    assert bad_resp.json()["detail"] == "人工处理必须选择消息推送途径"

    ok_resp = await client.post(
        "/v1/admin/skus",
        json={
            "skill_id": skill_id,
            "name": "人工SKU",
            "delivery_mode": "human",
            "total_uses": 1,
            "push_channel_id": channel_id,
        },
        headers=headers,
    )
    assert ok_resp.status_code == 200
    assert ok_resp.json()["data"]["push_channel_id"] == channel_id


@pytest.mark.asyncio
async def test_human_xgj_purchase_creates_pending_order_without_token(
    client: AsyncClient,
    db_session,
):
    headers = await _admin_headers(client)
    channel_resp = await client.post(
        "/v1/admin/push-channels",
        json={"name": "Bark 通道", "provider": "bark", "base_url": "https://api.day.app/device-key"},
        headers=headers,
    )
    channel_id = channel_resp.json()["data"]["id"]

    skill_resp = await client.post("/v1/admin/skills", json={"name": "人工修复技能", "type": "prompt"}, headers=headers)
    skill_id = skill_resp.json()["data"]["id"]
    sku_resp = await client.post(
        "/v1/admin/skus",
        json={
            "skill_id": skill_id,
            "name": "老照片修复-人工处理",
            "delivery_mode": "human",
            "price_cents": 1680,
            "total_uses": 1,
            "push_channel_id": channel_id,
            "delivery_content_template": "人工处理中，请点击链接查看：{$卡密链接}",
        },
        headers=headers,
    )
    sku_id = sku_resp.json()["data"]["id"]

    purchase_resp = await _signed_post(
        client,
        "/xgj/open/goofish/order/purchase/create",
        {
            "order_no": "XGJ-HUMAN-ORDER-001",
            "goods_no": f"SKU-{sku_id}",
            "buy_quantity": 1,
            "notify_url": "https://example.com/callback/order",
            "biz_order_no": "BIZ-HUMAN-001",
        },
    )
    assert purchase_resp.status_code == 200
    purchase_payload = purchase_resp.json()
    assert purchase_payload["code"] == 0
    assert purchase_payload["data"]["order_status"] == 10
    assert "card_items" not in purchase_payload["data"]

    tokens = (await db_session.execute(select(Token))).scalars().all()
    assert tokens == []
    xgj_order = (await db_session.execute(select(XgjOrder))).scalar_one()
    assert xgj_order.status == 0
    assert xgj_order.local_token_id is None
    assert "token" not in xgj_order.delivery_info
    assert "token_url" not in xgj_order.delivery_info


@pytest.mark.asyncio
async def test_human_erp_push_notifies_bark_then_returns_template_card(
    client: AsyncClient,
    db_session,
    monkeypatch: pytest.MonkeyPatch,
):
    from app.api import xgj_erp as xgj_erp_api

    push_calls: list[dict] = []
    callback_calls: list[dict] = []

    async def fake_send_push_message(channel, *, title: str, body: str) -> dict:
        push_calls.append({"channel_id": str(channel.id), "title": title, "body": body})
        return {"code": 200}

    async def fake_notify_order_result(self, notify_url: str, order_data: dict):
        callback_calls.append({"notify_url": notify_url, "order_data": order_data})
        return {"code": 0, "msg": "OK"}

    monkeypatch.setattr(xgj_erp_api, "send_push_message", fake_send_push_message)
    monkeypatch.setattr(XGJVirtualClient, "notify_order_result", fake_notify_order_result)

    headers = await _admin_headers(client)
    channel_resp = await client.post(
        "/v1/admin/push-channels",
        json={"name": "Bark 通道", "provider": "bark", "base_url": "https://api.day.app/device-key"},
        headers=headers,
    )
    channel_id = channel_resp.json()["data"]["id"]

    skill_resp = await client.post("/v1/admin/skills", json={"name": "ERP人工技能", "type": "prompt"}, headers=headers)
    skill_id = skill_resp.json()["data"]["id"]
    sku_resp = await client.post(
        "/v1/admin/skus",
        json={
            "skill_id": skill_id,
            "name": "ERP人工SKU",
            "delivery_mode": "human",
            "price_cents": 1680,
            "total_uses": 1,
            "push_channel_id": channel_id,
            "delivery_content_template": "人工处理中，请按提示添加微信处理：{$卡密链接}",
        },
        headers=headers,
    )
    sku_id = sku_resp.json()["data"]["id"]

    purchase_resp = await _signed_post(
        client,
        "/xgj/open/goofish/order/purchase/create",
        {
            "order_no": "ERP-HUMAN-001",
            "goods_no": f"SKU-{sku_id}",
            "buy_quantity": 1,
            "notify_url": "https://example.com/callback/order",
            "biz_order_no": "ERP-HUMAN-001",
        },
    )
    assert purchase_resp.status_code == 200

    erp_resp = await _signed_erp_post(
        client,
        "/xgj/erp/push/order",
        {
            "order_no": "ERP-HUMAN-001",
            "biz_order_no": "ERP-HUMAN-001",
            "order_status": 10,
            "refund_status": 0,
            "order_type": 1,
        },
    )
    assert erp_resp.status_code == 200
    assert erp_resp.json()["result"] == "success"

    assert len(push_calls) == 1
    assert push_calls[0]["title"] == "需要人工处理"
    assert "ERP-HUMAN-001" in push_calls[0]["body"]

    assert len(callback_calls) == 1
    assert callback_calls[0]["notify_url"] == "https://example.com/callback/order"
    assert callback_calls[0]["order_data"]["order_status"] == 20
    assert "人工处理中，请按提示添加微信处理" in callback_calls[0]["order_data"]["card_items"][0]["card_pwd"]

    tokens = (await db_session.execute(select(Token))).scalars().all()
    assert tokens == []
    xgj_order = (await db_session.execute(select(XgjOrder))).scalar_one()
    assert xgj_order.status == 2
    assert xgj_order.delivery_info["human_erp_notified"] is True