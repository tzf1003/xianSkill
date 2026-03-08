from __future__ import annotations

import json
import time

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.domain.models import Goods, Order, Token, TokenStatus, XgjOrder
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


@pytest.fixture(autouse=True)
def _configure_virtual_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "XGJ_VIRTUAL_APP_KEY", "10001")
    monkeypatch.setattr(settings, "XGJ_VIRTUAL_APP_SECRET", "virtual-app-secret")
    monkeypatch.setattr(settings, "XGJ_VIRTUAL_MCH_ID", "20001")
    monkeypatch.setattr(settings, "XGJ_VIRTUAL_MCH_SECRET", "virtual-mch-secret")
    monkeypatch.setattr(settings, "BASE_URL", "http://testserver")
    monkeypatch.setattr(settings, "FRONTEND_BASE_URL", "https://frontend.example.com")


@pytest.mark.asyncio
async def test_admin_can_bind_single_spec_goods_to_local_sku(client: AsyncClient, db_session):
    headers = await _admin_headers(client)

    skill_resp = await client.post("/v1/admin/skills", json={"name": "虚拟货源技能", "type": "prompt"}, headers=headers)
    assert skill_resp.status_code == 200
    skill_id = skill_resp.json()["data"]["id"]

    sku_resp = await client.post(
        "/v1/admin/skus",
        json={"skill_id": skill_id, "name": "自动发货SKU", "total_uses": 1},
        headers=headers,
    )
    assert sku_resp.status_code == 200
    sku_id = sku_resp.json()["data"]["id"]

    goods = Goods(
        goods_no="LOCAL-G-001",
        goods_type=2,
        goods_name="本地卡密商品",
        price_cents=1999,
        stock=5,
        status=1,
        multi_spec=False,
    )
    db_session.add(goods)
    await db_session.commit()

    resp = await client.post(
        f"/v1/admin/goods/{goods.id}/specs",
        json={
            "spec_name": "默认",
            "price_cents": 1999,
            "stock": 5,
            "sku_bindings": [{"timing": "after_payment", "sku_id": sku_id}],
        },
        headers=headers,
    )
    assert resp.status_code == 200
    spec = resp.json()["data"]
    assert spec["spec_name"] == "默认"
    assert spec["sku_bindings"][0]["timing"] == "after_payment"
    assert spec["sku_bindings"][0]["sku_id"] == sku_id

    goods_resp = await client.get(f"/v1/admin/goods/{goods.id}", headers=headers)
    assert goods_resp.status_code == 200
    goods_data = goods_resp.json()["data"]
    assert goods_data["specs"][0]["sku_bindings"][0]["sku_id"] == sku_id


@pytest.mark.asyncio
async def test_xgj_virtual_purchase_order_creates_local_order_and_token(client: AsyncClient, db_session):
    headers = await _admin_headers(client)

    skill_resp = await client.post("/v1/admin/skills", json={"name": "卡密发货技能", "type": "prompt"}, headers=headers)
    assert skill_resp.status_code == 200
    skill_id = skill_resp.json()["data"]["id"]

    sku_resp = await client.post(
        "/v1/admin/skus",
        json={"skill_id": skill_id, "name": "卡密直发SKU", "delivery_mode": "auto", "total_uses": 2},
        headers=headers,
    )
    assert sku_resp.status_code == 200
    sku_id = sku_resp.json()["data"]["id"]

    goods = Goods(
        goods_no="LOCAL-G-002",
        goods_type=2,
        goods_name="技能兑换卡",
        price_cents=2999,
        stock=3,
        status=1,
        multi_spec=False,
    )
    db_session.add(goods)
    await db_session.commit()

    spec_resp = await client.post(
        f"/v1/admin/goods/{goods.id}/specs",
        json={
            "spec_name": "默认",
            "price_cents": 2999,
            "stock": 3,
            "sku_bindings": [{"timing": "after_payment", "sku_id": sku_id}],
        },
        headers=headers,
    )
    assert spec_resp.status_code == 200

    body = {
        "order_no": "XGJ-ORDER-001",
        "goods_no": goods.goods_no,
        "buy_quantity": 1,
        "notify_url": "https://example.com/callback/order",
        "biz_order_no": "BIZ-001",
    }
    resp = await _signed_post(client, "/xgj/open/goofish/order/purchase/create", body)
    assert resp.status_code == 200

    payload = resp.json()
    assert payload["code"] == 0
    data = payload["data"]
    assert data["order_status"] == 20
    assert data["goods_no"] == goods.goods_no
    assert data["card_items"][0]["card_pwd"].startswith("https://frontend.example.com/s/")

    detail_resp = await _signed_post(
        client,
        "/xgj/open/goofish/order/detail",
        {"order_no": body["order_no"]},
    )
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()["data"]
    assert detail_data["order_status"] == 20
    assert detail_data["card_items"][0]["card_pwd"] == data["card_items"][0]["card_pwd"]

    tokens_resp = await client.get("/v1/admin/tokens", headers=headers)
    assert tokens_resp.status_code == 200
    tokens = tokens_resp.json()["data"]["items"]
    assert len(tokens) == 1
    assert tokens[0]["total_uses"] == 2

    orders = (await db_session.execute(select(Order))).scalars().all()
    xgj_orders = (await db_session.execute(select(XgjOrder))).scalars().all()
    assert len(orders) == 1
    assert len(xgj_orders) == 1
    assert xgj_orders[0].delivery_info["token_url"] == data["card_items"][0]["card_pwd"]


@pytest.mark.asyncio
async def test_xgj_refund_notify_revokes_local_token(client: AsyncClient, db_session):
    headers = await _admin_headers(client)

    skill_resp = await client.post("/v1/admin/skills", json={"name": "退款测试技能", "type": "prompt"}, headers=headers)
    skill_id = skill_resp.json()["data"]["id"]
    sku_resp = await client.post(
        "/v1/admin/skus",
        json={"skill_id": skill_id, "name": "退款SKU", "delivery_mode": "auto", "total_uses": 1},
        headers=headers,
    )
    sku_id = sku_resp.json()["data"]["id"]

    goods = Goods(
        goods_no="LOCAL-G-003",
        goods_type=2,
        goods_name="退款商品",
        price_cents=999,
        stock=1,
        status=1,
        multi_spec=False,
    )
    db_session.add(goods)
    await db_session.commit()

    await client.post(
        f"/v1/admin/goods/{goods.id}/specs",
        json={
            "spec_name": "默认",
            "price_cents": 999,
            "stock": 1,
            "sku_bindings": [{"timing": "after_payment", "sku_id": sku_id}],
        },
        headers=headers,
    )

    order_body = {
        "order_no": "XGJ-ORDER-REFUND-001",
        "goods_no": goods.goods_no,
        "buy_quantity": 1,
        "notify_url": "https://example.com/callback/order",
        "biz_order_no": "BIZ-REFUND-001",
    }
    create_resp = await _signed_post(client, "/xgj/open/goofish/order/purchase/create", order_body)
    assert create_resp.status_code == 200

    refund_resp = await _signed_post(
        client,
        "/xgj/open/goofish/order/refund/notify",
        {"order_no": order_body["order_no"], "refund_amount": 999},
    )
    assert refund_resp.status_code == 200
    assert refund_resp.json()["result"] == "success"

    token = (await db_session.execute(select(Token))).scalar_one()
    assert token.status == TokenStatus.revoked


@pytest.mark.asyncio
async def test_xgj_goods_list_and_detail_follow_doc_shape(client: AsyncClient, db_session):
    headers = await _admin_headers(client)
    skill_resp = await client.post("/v1/admin/skills", json={"name": "直充技能", "type": "prompt"}, headers=headers)
    skill_id = skill_resp.json()["data"]["id"]
    sku_resp = await client.post(
        "/v1/admin/skus",
        json={"skill_id": skill_id, "name": "直充测试商品", "delivery_mode": "auto", "price_cents": 500, "total_uses": 1},
        headers=headers,
    )
    sku_id = sku_resp.json()["data"]["id"]
    goods_no = f"SKU-{sku_id}"

    list_resp = await _signed_post(
        client,
        "/xgj/open/goofish/goods/list",
        {"page_no": 1, "page_size": 100, "keyword": "直充测试商品", "goods_type": 2},
    )
    assert list_resp.status_code == 200
    list_payload = list_resp.json()
    assert list_payload["code"] == 0
    assert list_payload["data"]["count"] >= 1
    item = next(row for row in list_payload["data"]["list"] if row["goods_no"] == goods_no)
    assert item["goods_type"] == 2
    assert item["goods_name"] == "直充测试商品"
    assert item["price"] == 500
    assert item["stock"] == 999999
    assert item["status"] == 1
    assert isinstance(item["update_time"], int)
    assert isinstance(item["template"], list)
    assert item["template"] == []

    detail_resp = await _signed_post(
        client,
        "/xgj/open/goofish/goods/detail",
        {"goods_no": goods_no, "goods_type": 2},
    )
    assert detail_resp.status_code == 200
    detail = detail_resp.json()["data"]
    assert detail["goods_no"] == goods_no
    assert detail["goods_name"] == "直充测试商品"
    assert detail["price"] == 500
    assert isinstance(detail["template"], list)
    assert detail["template"] == []


@pytest.mark.asyncio
async def test_xgj_goods_list_supports_partial_goods_no_keyword(client: AsyncClient, db_session):
    headers = await _admin_headers(client)
    skill_resp = await client.post("/v1/admin/skills", json={"name": "编码搜索技能", "type": "prompt"}, headers=headers)
    skill_id = skill_resp.json()["data"]["id"]
    sku_resp = await client.post(
        "/v1/admin/skus",
        json={"skill_id": skill_id, "name": "部分编码搜索商品", "delivery_mode": "auto", "price_cents": 800, "total_uses": 1},
        headers=headers,
    )
    sku_id = sku_resp.json()["data"]["id"]
    goods_no = f"SKU-{sku_id}"
    partial_keyword = sku_id.split("-")[0]

    resp = await _signed_post(
        client,
        "/xgj/open/goofish/goods/list",
        {"page_no": 1, "page_size": 100, "keyword": partial_keyword, "goods_type": 2},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["code"] == 0
    assert any(item["goods_no"] == goods_no for item in payload["data"]["list"])


@pytest.mark.asyncio
async def test_xgj_goods_list_supports_bound_sku_name_keyword(client: AsyncClient, db_session):
    headers = await _admin_headers(client)

    skill_resp = await client.post("/v1/admin/skills", json={"name": "照片处理", "type": "prompt"}, headers=headers)
    skill_id = skill_resp.json()["data"]["id"]
    sku_resp = await client.post(
        "/v1/admin/skus",
        json={"skill_id": skill_id, "name": "老照片修复-自动", "delivery_mode": "auto", "total_uses": 1},
        headers=headers,
    )
    sku_id = sku_resp.json()["data"]["id"]

    resp = await _signed_post(
        client,
        "/xgj/open/goofish/goods/list",
        {"page_no": 1, "page_size": 100, "keyword": "老", "goods_type": 2},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["code"] == 0
    assert any(item["goods_no"] == f"SKU-{sku_id}" for item in payload["data"]["list"])


@pytest.mark.asyncio
async def test_xgj_virtual_purchase_order_can_use_sku_goods_no(client: AsyncClient, db_session):
    headers = await _admin_headers(client)

    skill_resp = await client.post("/v1/admin/skills", json={"name": "SKU直发技能", "type": "prompt"}, headers=headers)
    skill_id = skill_resp.json()["data"]["id"]
    sku_resp = await client.post(
        "/v1/admin/skus",
        json={"skill_id": skill_id, "name": "老照片修复-自动", "delivery_mode": "auto", "price_cents": 1680, "total_uses": 1},
        headers=headers,
    )
    sku_id = sku_resp.json()["data"]["id"]
    goods_no = f"SKU-{sku_id}"

    resp = await _signed_post(
        client,
        "/xgj/open/goofish/order/purchase/create",
        {
            "order_no": "XGJ-SKU-ORDER-001",
            "goods_no": goods_no,
            "buy_quantity": 1,
            "notify_url": "https://example.com/callback/order",
            "biz_order_no": "BIZ-SKU-001",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["code"] == 0
    assert payload["data"]["goods_no"] == goods_no
    assert payload["data"]["goods_name"] == "老照片修复-自动"
    assert payload["data"]["card_items"][0]["card_pwd"].startswith("https://frontend.example.com/s/")