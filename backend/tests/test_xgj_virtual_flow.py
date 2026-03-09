from __future__ import annotations

import json
import time

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.domain.models import Goods, Order, Token, TokenStatus, XgjOrder
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
        json={
            "skill_id": skill_id,
            "name": "卡密直发SKU",
            "delivery_mode": "auto",
            "total_uses": 2,
            "delivery_content_template": "您的订单编号为：{$订单编号}，您的卡密信息为：{$卡密信息}\n请在此处点击链接，按照提示操作，即可使用：{$卡密链接}",
        },
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
    assert body["order_no"] in data["card_items"][0]["card_pwd"]

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
    token_url = xgj_orders[0].delivery_info["token_url"]
    token_value = xgj_orders[0].delivery_info["token"]
    expected_content = (
        f"您的订单编号为：{body['order_no']}，您的卡密信息为：{token_value}\n"
        f"请在此处点击链接，按照提示操作，即可使用：{token_url}"
    )
    assert "card_no" not in data["card_items"][0]
    assert data["card_items"][0]["card_pwd"] == expected_content
    assert detail_data["card_items"][0]["card_pwd"] == expected_content
    assert xgj_orders[0].delivery_info["delivery_content"] == expected_content


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
async def test_admin_can_grant_more_uses_to_active_token(client: AsyncClient):
    headers = await _admin_headers(client)

    skill_resp = await client.post("/v1/admin/skills", json={"name": "增次测试技能", "type": "prompt"}, headers=headers)
    assert skill_resp.status_code == 200
    skill_id = skill_resp.json()["data"]["id"]

    sku_resp = await client.post(
        "/v1/admin/skus",
        json={"skill_id": skill_id, "name": "增次测试SKU", "delivery_mode": "auto", "total_uses": 2},
        headers=headers,
    )
    assert sku_resp.status_code == 200
    sku_id = sku_resp.json()["data"]["id"]

    token_resp = await client.post(
        "/v1/admin/tokens",
        json={"sku_id": sku_id},
        headers=headers,
    )
    assert token_resp.status_code == 200
    token_id = token_resp.json()["data"]["id"]
    assert token_resp.json()["data"]["total_uses"] == 2
    assert token_resp.json()["data"]["remaining"] == 2

    grant_resp = await client.post(
        f"/v1/admin/tokens/{token_id}/grant-uses",
        json={"uses": 3},
        headers=headers,
    )
    assert grant_resp.status_code == 200
    data = grant_resp.json()["data"]
    assert data["total_uses"] == 5
    assert data["remaining"] == 5


@pytest.mark.asyncio
async def test_xgj_ticket_order_uses_sku_delivery_template(client: AsyncClient, db_session):
    headers = await _admin_headers(client)

    skill_resp = await client.post("/v1/admin/skills", json={"name": "券码模板技能", "type": "prompt"}, headers=headers)
    skill_id = skill_resp.json()["data"]["id"]
    sku_resp = await client.post(
        "/v1/admin/skus",
        json={
            "skill_id": skill_id,
            "name": "券码自动发货SKU",
            "delivery_mode": "auto",
            "total_uses": 1,
            "delivery_content_template": "订单：{$订单编号}；卡密：{$卡密信息}；链接：{$卡密链接}",
        },
        headers=headers,
    )
    sku_id = sku_resp.json()["data"]["id"]

    goods = Goods(
        goods_no="LOCAL-G-004",
        goods_type=3,
        goods_name="券码商品",
        price_cents=1299,
        stock=2,
        status=1,
        multi_spec=False,
    )
    db_session.add(goods)
    await db_session.commit()

    await client.post(
        f"/v1/admin/goods/{goods.id}/specs",
        json={
            "spec_name": "默认",
            "price_cents": 1299,
            "stock": 2,
            "sku_bindings": [{"timing": "after_payment", "sku_id": sku_id}],
        },
        headers=headers,
    )

    body = {
        "order_no": "XGJ-TICKET-001",
        "goods_no": goods.goods_no,
        "buy_quantity": 1,
        "notify_url": "https://example.com/callback/order",
        "biz_order_no": "BIZ-TICKET-001",
    }
    resp = await _signed_post(client, "/xgj/open/goofish/order/ticket/create", body)
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["code"] == 0

    data = payload["data"]
    xgj_order = (await db_session.execute(select(XgjOrder).where(XgjOrder.order_no == body["order_no"]))).scalar_one()
    token_url = xgj_order.delivery_info["token_url"]
    expected_content = f"订单：{body['order_no']}；卡密：{data['ticket_items'][0]['code_no']}；链接：{token_url}"
    assert data["ticket_items"][0]["code_pwd"] == expected_content
    assert xgj_order.delivery_info["delivery_content"] == expected_content


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
async def test_xgj_goods_list_includes_human_delivery_sku(client: AsyncClient, db_session):
    headers = await _admin_headers(client)

    channel_resp = await client.post(
        "/v1/admin/push-channels",
        json={"name": "Bark 通道", "provider": "bark", "base_url": "https://api.day.app/device-key"},
        headers=headers,
    )
    channel_id = channel_resp.json()["data"]["id"]

    skill_resp = await client.post("/v1/admin/skills", json={"name": "人工处理技能", "type": "prompt"}, headers=headers)
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
        },
        headers=headers,
    )
    sku_id = sku_resp.json()["data"]["id"]

    resp = await _signed_post(
        client,
        "/xgj/open/goofish/goods/list",
        {"page_no": 1, "page_size": 100, "keyword": "人工处理", "goods_type": 2},
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
    assert "https://frontend.example.com/s/" in payload["data"]["card_items"][0]["card_pwd"]


@pytest.mark.asyncio
async def test_xgj_receipt_reward_order_grants_token_uses(client: AsyncClient, db_session):
    """下单收货赠送 SKU 时，直接给原始基础订单的 Token 加次数，返回原 Token 发货内容。"""
    headers = await _admin_headers(client)

    skill_resp = await client.post("/v1/admin/skills", json={"name": "收货赠送技能", "type": "prompt"}, headers=headers)
    skill_id = skill_resp.json()["data"]["id"]

    # 基础 auto SKU
    base_sku_resp = await client.post(
        "/v1/admin/skus",
        json={
            "skill_id": skill_id,
            "name": "基础自动SKU",
            "delivery_mode": "auto",
            "price_cents": 1680,
            "total_uses": 1,
        },
        headers=headers,
    )
    base_sku_id = base_sku_resp.json()["data"]["id"]

    # 收货赠送 SKU
    reward_sku_resp = await client.post(
        "/v1/admin/skus",
        json={
            "skill_id": skill_id,
            "name": "收货赠送SKU",
            "delivery_mode": "after_receipt",
            "price_cents": 0,
            "total_uses": 3,
        },
        headers=headers,
    )
    reward_sku_id = reward_sku_resp.json()["data"]["id"]

    # 1. 先下基础订单
    base_resp = await _signed_post(
        client,
        "/xgj/open/goofish/order/purchase/create",
        {
            "order_no": "XGJ-BASE-001",
            "goods_no": f"SKU-{base_sku_id}",
            "buy_quantity": 1,
            "notify_url": "https://example.com/callback/order",
            "biz_order_no": "PLATFORM-RECEIPT-001",
        },
    )
    assert base_resp.status_code == 200
    assert base_resp.json()["code"] == 0

    base_token = (await db_session.execute(select(Token))).scalar_one()
    assert base_token.total_uses == 1

    # 2. 再下收货赠送订单（同 biz_order_no）
    reward_resp = await _signed_post(
        client,
        "/xgj/open/goofish/order/purchase/create",
        {
            "order_no": "XGJ-REWARD-RECEIPT-001",
            "goods_no": f"SKU-{reward_sku_id}",
            "buy_quantity": 1,
            "notify_url": "https://example.com/callback/order",
            "biz_order_no": "PLATFORM-RECEIPT-001",
        },
    )
    assert reward_resp.status_code == 200
    reward_data = reward_resp.json()
    assert reward_data["code"] == 0

    # 3. 验证 Token 加过次数了
    await db_session.refresh(base_token)
    assert base_token.total_uses == 4  # 1 + 3

    # 4. 验证发货内容使用的是原始 Token
    reward_card_pwd = reward_data["data"]["card_items"][0]["card_pwd"]
    assert base_token.token in reward_card_pwd
    token_url = f"https://frontend.example.com/s/{base_token.token}"
    assert token_url in reward_card_pwd

    # 5. 验证 XGJ 赠送订单记录正确链接到原始 Token
    reward_xgj = (
        await db_session.execute(select(XgjOrder).where(XgjOrder.order_no == "XGJ-REWARD-RECEIPT-001"))
    ).scalar_one()
    assert reward_xgj.local_token_id == base_token.id
    assert reward_xgj.delivery_info["reward_type"] == "after_receipt"
    assert reward_xgj.delivery_info["reward_uses_granted"] == 3


@pytest.mark.asyncio
async def test_xgj_review_reward_order_grants_token_uses(client: AsyncClient, db_session):
    """下单好评赠送 SKU 时，直接给原始基础订单的 Token 加次数，返回原 Token 发货内容。"""
    headers = await _admin_headers(client)

    skill_resp = await client.post("/v1/admin/skills", json={"name": "好评赠送技能", "type": "prompt"}, headers=headers)
    skill_id = skill_resp.json()["data"]["id"]

    # 基础 auto SKU
    base_sku_resp = await client.post(
        "/v1/admin/skus",
        json={
            "skill_id": skill_id,
            "name": "基础自动SKU-好评",
            "delivery_mode": "auto",
            "price_cents": 990,
            "total_uses": 1,
        },
        headers=headers,
    )
    base_sku_id = base_sku_resp.json()["data"]["id"]

    # 好评赠送 SKU
    reward_sku_resp = await client.post(
        "/v1/admin/skus",
        json={
            "skill_id": skill_id,
            "name": "好评赠送SKU",
            "delivery_mode": "after_review",
            "price_cents": 0,
            "total_uses": 2,
        },
        headers=headers,
    )
    reward_sku_id = reward_sku_resp.json()["data"]["id"]

    # 1. 先下基础订单
    base_resp = await _signed_post(
        client,
        "/xgj/open/goofish/order/purchase/create",
        {
            "order_no": "XGJ-BASE-REVIEW-001",
            "goods_no": f"SKU-{base_sku_id}",
            "buy_quantity": 1,
            "notify_url": "https://example.com/callback/order",
            "biz_order_no": "PLATFORM-REVIEW-001",
        },
    )
    assert base_resp.status_code == 200

    base_token = (await db_session.execute(select(Token))).scalar_one()
    assert base_token.total_uses == 1

    # 2. 再下好评赠送订单
    reward_resp = await _signed_post(
        client,
        "/xgj/open/goofish/order/purchase/create",
        {
            "order_no": "XGJ-REWARD-REVIEW-001",
            "goods_no": f"SKU-{reward_sku_id}",
            "buy_quantity": 1,
            "notify_url": "https://example.com/callback/order",
            "biz_order_no": "PLATFORM-REVIEW-001",
        },
    )
    assert reward_resp.status_code == 200
    reward_data = reward_resp.json()
    assert reward_data["code"] == 0

    # 3. 验证 Token 加了次数
    await db_session.refresh(base_token)
    assert base_token.total_uses == 3  # 1 + 2

    # 4. 发货内容包含原始 Token
    reward_card_pwd = reward_data["data"]["card_items"][0]["card_pwd"]
    assert base_token.token in reward_card_pwd

    # 5. 公开接口也能看到更新后的余量
    token_info_resp = await client.get(f"/v1/public/token/{base_token.token}")
    assert token_info_resp.status_code == 200
    assert token_info_resp.json()["data"]["remaining"] == 3


@pytest.mark.asyncio
async def test_xgj_reward_same_order_no(client: AsyncClient, db_session):
    """XGJ 用同一 order_no 下基础订单和赠送订单（真实 XGJ 行为）。"""
    headers = await _admin_headers(client)

    skill_resp = await client.post("/v1/admin/skills", json={"name": "同号赠送技能", "type": "prompt"}, headers=headers)
    skill_id = skill_resp.json()["data"]["id"]

    base_sku_resp = await client.post(
        "/v1/admin/skus",
        json={
            "skill_id": skill_id,
            "name": "同号基础SKU",
            "delivery_mode": "auto",
            "price_cents": 1680,
            "total_uses": 1,
            "delivery_content_template": "基础：{$卡密链接}",
        },
        headers=headers,
    )
    base_sku_id = base_sku_resp.json()["data"]["id"]

    reward_sku_resp = await client.post(
        "/v1/admin/skus",
        json={
            "skill_id": skill_id,
            "name": "同号收货赠送SKU",
            "delivery_mode": "after_receipt",
            "price_cents": 0,
            "total_uses": 2,
            "delivery_content_template": "赠送：{$卡密链接}",
        },
        headers=headers,
    )
    reward_sku_id = reward_sku_resp.json()["data"]["id"]

    # 1. 基础订单
    base_resp = await _signed_post(
        client,
        "/xgj/open/goofish/order/purchase/create",
        {
            "order_no": "SAME-ORDER-001",
            "goods_no": f"SKU-{base_sku_id}",
            "buy_quantity": 1,
        },
    )
    assert base_resp.status_code == 200
    assert base_resp.json()["code"] == 0
    base_card_pwd = base_resp.json()["data"]["card_items"][0]["card_pwd"]

    base_token = (await db_session.execute(select(Token))).scalar_one()
    assert base_token.total_uses == 1
    token_url = f"https://frontend.example.com/s/{base_token.token}"
    assert token_url in base_card_pwd

    # 2. 赠送订单，用同一个 order_no（XGJ 真实行为）
    reward_resp = await _signed_post(
        client,
        "/xgj/open/goofish/order/purchase/create",
        {
            "order_no": "SAME-ORDER-001",
            "goods_no": f"SKU-{reward_sku_id}",
            "buy_quantity": 1,
        },
    )
    assert reward_resp.status_code == 200
    reward_data = reward_resp.json()
    assert reward_data["code"] == 0

    # 3. Token 已加次数
    await db_session.refresh(base_token)
    assert base_token.total_uses == 3  # 1 + 2

    # 4. 赠送返回的发货内容包含原始 Token
    reward_card_pwd = reward_data["data"]["card_items"][0]["card_pwd"]
    assert token_url in reward_card_pwd
    assert reward_card_pwd.startswith("赠送：")

    # 5. 数据库只有一条 XgjOrder 记录（同 order_no 不重复插入）
    all_xgj = (await db_session.execute(select(XgjOrder))).scalars().all()
    assert len(all_xgj) == 1
    assert all_xgj[0].order_no == "SAME-ORDER-001"
    assert all_xgj[0].delivery_info.get("reward_type") == "after_receipt"
    assert all_xgj[0].delivery_info.get("reward_uses_granted") == 2