from __future__ import annotations

import httpx
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.domain.models import DeliveryTiming, Goods, SKU, Skill, SkillType, SpecSkuBinding


async def _admin_headers(client):
    resp = await client.post("/v1/admin/login", json={
        "username": settings.ADMIN_USERNAME,
        "password": settings.ADMIN_PASSWORD,
    })
    assert resp.status_code == 200
    token = resp.json()["data"]["token"]
    return {"Authorization": f"Bearer {token}"}


class FakeErpClient:
    def __init__(self):
        self.sku_requests: list[list[int]] = []
        self.sku_items = [
            {
                "sku_id": 1,
                "price": 1000,
                "stock": 3,
                "sku_text": "面值:月卡;类型:直充",
                "outer_id": "VIP-001-A",
            },
            {
                "sku_id": 2,
                "price": 2000,
                "stock": 4,
                "sku_text": "面值:季卡;类型:直充",
                "outer_id": "VIP-001-B",
            },
        ]
        self.products = {
            10001: {
                "product_id": 10001,
                "product_status": 22,
                "item_biz_type": 2,
                "sp_biz_type": 25,
                "channel_cat_id": "cat-card",
                "channel_pv": [
                    {
                        "property_id": "p1",
                        "property_name": "面值",
                        "value_id": "v1",
                        "value_name": "100元",
                    }
                ],
                "title": "腾讯视频会员",
                "price": 1000,
                "original_price": 1200,
                "express_fee": 0,
                "stock": 7,
                "outer_id": "VIP-001",
                "stuff_status": 0,
                "publish_status": 3,
                "publish_shop": [
                    {
                        "user_name": "shop_a",
                        "province": 110000,
                        "city": 110100,
                        "district": 110101,
                        "title": "腾讯视频会员",
                        "content": "自动发货，秒到账",
                        "images": ["https://img.example.com/vip-1.png"],
                        "service_support": "VNR",
                    }
                ],
                "spec_type": 2,
                "sku_items": list(self.sku_items),
                "flash_sale_type": None,
                "is_tax_included": False,
            }
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get_product_list(self, **kwargs):
        return {
            "list": [
                {
                    "product_id": 10001,
                    "product_status": 22,
                    "item_biz_type": 2,
                    "sp_biz_type": 25,
                    "channel_cat_id": "cat-card",
                    "original_price": 1200,
                    "price": 1000,
                    "stock": 7,
                    "sold": 0,
                    "title": "腾讯视频会员",
                    "district_id": 110101,
                    "outer_id": "VIP-001",
                    "stuff_status": 0,
                    "express_fee": 0,
                    "spec_type": 2,
                    "source": 91,
                    "specify_publish_time": 0,
                    "online_time": 0,
                    "offline_time": 0,
                    "sold_time": 0,
                    "update_time": 1700000000,
                    "create_time": 1700000000,
                }
            ],
            "count": 1,
            "page_no": 1,
            "page_size": kwargs.get("page_size", 100),
        }

    async def get_product_detail(self, product_id: int):
        return self.products[product_id]

    async def get_product_sku(self, product_id: int | list[int]):
        product_ids = product_id if isinstance(product_id, list) else [product_id]
        self.sku_requests.append(product_ids)
        return {
            "list": [
                {
                    "product_id": product_ids[0],
                    "sku_items": list(self.sku_items),
                }
            ]
        }


class FakeErpClientWithoutDetailSku(FakeErpClient):
    def __init__(self):
        super().__init__()
        self.products[10001].pop("sku_items", None)


class FakeErpClientRenamedSku(FakeErpClientWithoutDetailSku):
    def __init__(self):
        super().__init__()
        self.sku_items = [
            {
                "sku_id": 1,
                "price": 1100,
                "stock": 5,
                "sku_text": "面值:月卡;类型:官方直连",
                "outer_id": "VIP-001-A-NEW",
            },
            {
                "sku_id": 2,
                "price": 2100,
                "stock": 6,
                "sku_text": "面值:季卡;类型:官方直连",
                "outer_id": "VIP-001-B-NEW",
            },
        ]


class FakeErpClientSku400(FakeErpClient):
    def __init__(self):
        super().__init__()
        self.products[10001].pop("sku_items", None)

    async def get_product_sku(self, product_id: int | list[int]):
        request = httpx.Request("POST", "https://open.goofish.pro/api/open/product/sku/list")
        response = httpx.Response(400, request=request)
        raise httpx.HTTPStatusError("bad request", request=request, response=response)


@pytest.mark.asyncio
async def test_sync_xgj_goods_creates_local_goods(client, db_session, monkeypatch):
    from app.api.admin_routes import xgj_support

    fake_client = FakeErpClient()
    monkeypatch.setattr(xgj_support, "get_erp_client", lambda: fake_client)
    headers = await _admin_headers(client)

    resp = await client.post("/v1/admin/goods/sync", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data == {"synced": 1, "created": 1, "updated": 0, "failed": 0}

    goods = (await db_session.execute(select(Goods))).scalar_one()
    assert goods.goods_no == "VIP-001"
    assert goods.goods_name == "腾讯视频会员"
    assert goods.goods_type == 3
    assert goods.xgj_goods_id == "10001"
    assert goods.logo_url == "https://img.example.com/vip-1.png"
    assert goods.price_cents == 1000
    assert goods.stock == 7
    assert goods.status == 1
    assert goods.multi_spec is True
    assert {spec.xgj_sku_id for spec in goods.specs} == {"1", "2"}
    assert goods.spec_groups == [
        {"name": "面值", "values": ["月卡", "季卡"]},
        {"name": "类型", "values": ["直充"]},
    ]
    assert fake_client.sku_requests == []

    detail_resp = await client.get(f"/v1/admin/goods/{goods.id}", headers=headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()["data"]
    assert detail["xgj_profile"]["channel_cat_id"] == "cat-card"
    assert detail["xgj_profile"]["product_status"] == 22
    assert detail["xgj_profile"]["publish_status"] == 3
    assert detail["xgj_properties"][0]["property_name"] == "面值"
    assert detail["xgj_publish_shops"][0]["user_name"] == "shop_a"
    assert detail["xgj_publish_shops"][0]["images"][0]["image_url"] == "https://img.example.com/vip-1.png"
    assert len(detail["specs"]) == 2
    assert {spec["spec_name"] for spec in detail["specs"]} == {"月卡/直充", "季卡/直充"}

    resp = await client.post("/v1/admin/goods/sync", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data == {"synced": 1, "created": 0, "updated": 1, "failed": 0}

    total = len((await db_session.execute(select(Goods))).scalars().all())
    assert total == 1


@pytest.mark.asyncio
async def test_goods_management_is_read_only(client, db_session):
    headers = await _admin_headers(client)

    goods = Goods(
        goods_no="LOCAL-001",
        goods_type=3,
        goods_name="本地商品",
        price_cents=100,
        stock=1,
        status=1,
        multi_spec=False,
        xgj_properties=[],
        xgj_publish_shops=[],
        specs=[],
    )
    db_session.add(goods)
    await db_session.commit()
    await db_session.refresh(goods)

    create_resp = await client.post("/v1/admin/goods", headers=headers, json={
        "goods_type": 3,
        "goods_name": "禁止创建",
        "xgj_profile": {
            "item_biz_type": 2,
            "sp_biz_type": 22,
            "category_id": None,
            "channel_cat_id": "cat",
            "original_price_cents": 0,
            "express_fee_cents": 0,
            "stuff_status": 0,
            "notify_url": None,
            "flash_sale_type": None,
            "is_tax_included": False,
        },
        "xgj_publish_shops": [{
            "xgj_shop_id": None,
            "user_name": "shop-a",
            "province": 110000,
            "city": 110100,
            "district": 110101,
            "title": "禁止创建",
            "content": "只读模式禁止本地创建商品",
            "white_image_url": None,
            "service_support": None,
            "sort_order": 0,
            "images": [{"image_url": "https://img.example.com/a.png", "sort_order": 0}],
        }],
    })
    assert create_resp.status_code == 405

    update_resp = await client.patch(f"/v1/admin/goods/{goods.id}", headers=headers, json={"goods_name": "禁止修改"})
    assert update_resp.status_code == 405

    delete_resp = await client.delete(f"/v1/admin/goods/{goods.id}", headers=headers)
    assert delete_resp.status_code == 405


@pytest.mark.asyncio
async def test_sync_xgj_goods_tolerates_sku_400(client, db_session, monkeypatch):
    from app.api.admin_routes import xgj_support

    monkeypatch.setattr(xgj_support, "get_erp_client", lambda: FakeErpClientSku400())
    headers = await _admin_headers(client)

    resp = await client.post("/v1/admin/goods/sync", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data == {"synced": 1, "created": 1, "updated": 0, "failed": 0}

    goods = (await db_session.execute(select(Goods))).scalar_one()
    assert goods.multi_spec is True
    assert goods.specs == []


@pytest.mark.asyncio
async def test_sync_xgj_goods_fetches_sku_list_with_array_payload(client, db_session, monkeypatch):
    from app.api.admin_routes import xgj_support

    fake_client = FakeErpClientWithoutDetailSku()
    monkeypatch.setattr(xgj_support, "get_erp_client", lambda: fake_client)
    headers = await _admin_headers(client)

    resp = await client.post("/v1/admin/goods/sync", headers=headers)
    assert resp.status_code == 200

    goods = (await db_session.execute(select(Goods))).scalar_one()
    assert goods.multi_spec is True
    assert len(goods.specs) == 2
    assert fake_client.sku_requests == [[10001]]


@pytest.mark.asyncio
async def test_sync_xgj_goods_preserves_local_sku_bindings_by_xgj_sku_id(client, db_session, monkeypatch):
    from app.api.admin_routes import xgj_support

    first_client = FakeErpClientWithoutDetailSku()
    monkeypatch.setattr(xgj_support, "get_erp_client", lambda: first_client)
    headers = await _admin_headers(client)

    first_resp = await client.post("/v1/admin/goods/sync", headers=headers)
    assert first_resp.status_code == 200

    goods = (await db_session.execute(select(Goods))).scalar_one()
    first_spec = sorted(goods.specs, key=lambda spec: spec.xgj_sku_id or "")[0]

    skill = Skill(name="测试技能", type=SkillType.prompt)
    db_session.add(skill)
    await db_session.flush()

    local_sku = SKU(skill_id=skill.id, name="本地SKU")
    db_session.add(local_sku)
    await db_session.flush()

    db_session.add(
        SpecSkuBinding(
            spec_id=first_spec.id,
            timing=DeliveryTiming.after_payment,
            sku_id=local_sku.id,
        )
    )
    await db_session.commit()

    renamed_client = FakeErpClientRenamedSku()
    monkeypatch.setattr(xgj_support, "get_erp_client", lambda: renamed_client)
    second_resp = await client.post("/v1/admin/goods/sync", headers=headers)
    assert second_resp.status_code == 200

    db_session.expire_all()
    refreshed_goods = (await db_session.execute(select(Goods))).scalar_one()
    refreshed_spec = next(spec for spec in refreshed_goods.specs if spec.xgj_sku_id == "1")
    assert refreshed_spec.spec_name == "月卡/官方直连"
    assert refreshed_spec.xgj_outer_id == "VIP-001-A-NEW"
    assert len(refreshed_spec.sku_bindings) == 1
    assert refreshed_spec.sku_bindings[0].sku_id == local_sku.id


@pytest.mark.asyncio
async def test_sync_xgj_goods_preserves_existing_specs_when_sku_sync_degraded(client, db_session, monkeypatch):
    from app.api.admin_routes import xgj_support

    monkeypatch.setattr(xgj_support, "get_erp_client", lambda: FakeErpClientSku400())
    headers = await _admin_headers(client)

    first_resp = await client.post("/v1/admin/goods/sync", headers=headers)
    assert first_resp.status_code == 200

    monkeypatch.setattr(xgj_support, "get_erp_client", lambda: FakeErpClient())
    second_resp = await client.post("/v1/admin/goods/sync", headers=headers)
    assert second_resp.status_code == 200

    monkeypatch.setattr(xgj_support, "get_erp_client", lambda: FakeErpClientSku400())
    third_resp = await client.post("/v1/admin/goods/sync", headers=headers)
    assert third_resp.status_code == 200

    goods = (await db_session.execute(select(Goods))).scalar_one()
    assert goods.multi_spec is True
    assert len(goods.specs) == 2
    assert {spec.spec_name for spec in goods.specs} == {"月卡/直充", "季卡/直充"}
