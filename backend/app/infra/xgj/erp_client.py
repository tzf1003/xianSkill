"""
闲管家开放平台（进销存 / ERP）客户端。

签名规则：``md5(appKey + "," + md5(body) + "," + timestamp + "," + appSecret)``
请求格式：``POST {domain}{path}?appid={appKey}&timestamp={timestamp}&sign={sign}``
域名：``https://open.goofish.pro``

完整覆盖的接口列表：
  - 用户：查询闲鱼店铺
  - 商品：类目 / 属性 / 列表 / 详情 / 规格 / 创建(单个/批量) / 上架 / 下架 / 编辑 / 编辑库存 / 删除
  - 订单：列表 / 详情 / 卡密列表 / 物流发货 / 修改价格
  - 其他：查询快递公司
"""

from __future__ import annotations

from typing import Any

from .base_client import XGJBaseClient

_DOMAIN = "https://open.goofish.pro"


class XGJErpClient(XGJBaseClient):
    """闲管家开放平台（进销存 / ERP）客户端。"""

    BASE_URL = _DOMAIN

    # ------------------------------------------------------------------
    # 签名 & URL
    # ------------------------------------------------------------------

    def _build_sign(self, body_json: str, timestamp: int) -> str:
        body_md5 = self._md5(body_json)
        raw = f"{self.app_key},{body_md5},{timestamp},{self.app_secret}"
        return self._md5(raw)

    def _build_url(self, path: str, timestamp: int, sign: str) -> str:
        return f"{_DOMAIN}{path}?appid={self.app_key}&timestamp={timestamp}&sign={sign}"

    # ==================================================================
    # 用户
    # ==================================================================

    async def get_shops(self) -> Any:
        """查询闲鱼店铺列表。"""
        return await self.request("/api/open/user/authorize/list")

    # ==================================================================
    # 商品
    # ==================================================================

    async def get_categories(
        self,
        item_biz_type: int,
        sp_biz_type: int | None = None,
        flash_sale_type: int | None = None,
    ) -> Any:
        """查询商品类目。"""
        body: dict[str, Any] = {"item_biz_type": item_biz_type}
        if sp_biz_type is not None:
            body["sp_biz_type"] = sp_biz_type
        if flash_sale_type is not None:
            body["flash_sale_type"] = flash_sale_type
        return await self.request("/api/open/product/category/list", body)

    async def get_product_properties(
        self,
        item_biz_type: int,
        sp_biz_type: int,
        channel_cat_id: str,
        sub_property_id: str | None = None,
    ) -> Any:
        """查询商品属性。"""
        body: dict[str, Any] = {
            "item_biz_type": item_biz_type,
            "sp_biz_type": sp_biz_type,
            "channel_cat_id": channel_cat_id,
        }
        if sub_property_id is not None:
            body["sub_property_id"] = sub_property_id
        return await self.request("/api/open/product/pv/list", body)

    async def get_product_list(
        self,
        *,
        product_status: int | None = None,
        sale_status: int | None = None,
        update_time: list[int] | None = None,
        create_time: list[int] | None = None,
        page_no: int = 1,
        page_size: int = 50,
        **kwargs: Any,
    ) -> Any:
        """查询商品列表。"""
        body: dict[str, Any] = {"page_no": page_no, "page_size": page_size}
        if product_status is not None:
            body["product_status"] = product_status
        if sale_status is not None:
            body["sale_status"] = sale_status
        if update_time is not None:
            body["update_time"] = update_time
        if create_time is not None:
            body["create_time"] = create_time
        body.update(kwargs)
        return await self.request("/api/open/product/list", body)

    async def get_product_detail(self, product_id: int) -> Any:
        """查询商品详情。"""
        return await self.request(
            "/api/open/product/detail", {"product_id": product_id}
        )

    async def get_product_sku(self, product_id: int | list[int]) -> Any:
        """查询商品规格（仅多规格商品）。"""
        product_ids = product_id if isinstance(product_id, list) else [product_id]
        return await self.request(
            "/api/open/product/sku/list", {"product_id": product_ids}
        )

    async def create_product(self, product_data: dict[str, Any]) -> Any:
        """创建商品（单个）。"""
        return await self.request("/api/open/product/create", product_data)

    async def create_products_batch(self, products: list[dict[str, Any]]) -> Any:
        """创建商品（批量）。"""
        return await self.request("/api/open/product/batch/create", {"list": products})

    async def publish_product(
        self,
        product_id: int,
        user_name: list[str],
        *,
        specify_publish_time: str | None = None,
        notify_url: str | None = None,
    ) -> Any:
        """上架商品。"""
        body: dict[str, Any] = {
            "product_id": product_id,
            "user_name": user_name,
        }
        if specify_publish_time is not None:
            body["specify_publish_time"] = specify_publish_time
        if notify_url is not None:
            body["notify_url"] = notify_url
        return await self.request("/api/open/product/publish", body)

    async def unpublish_product(self, product_id: int) -> Any:
        """下架商品。"""
        return await self.request(
            "/api/open/product/downShelf", {"product_id": product_id}
        )

    async def edit_product(self, product_data: dict[str, Any]) -> Any:
        """编辑商品（仅传入需要更新的字段即可）。"""
        return await self.request("/api/open/product/edit", product_data)

    async def edit_stock(self, stock_data: dict[str, Any]) -> Any:
        """编辑库存。"""
        return await self.request("/api/open/product/edit/stock", stock_data)

    async def delete_product(self, product_id: int) -> Any:
        """删除商品（仅草稿箱/待发布状态）。"""
        return await self.request(
            "/api/open/product/delete", {"product_id": product_id}
        )

    # ==================================================================
    # 订单
    # ==================================================================

    async def get_order_list(
        self,
        *,
        authorize_id: int | None = None,
        order_status: int | None = None,
        refund_status: int | None = None,
        pay_time: list[int] | None = None,
        update_time: list[int] | None = None,
        page_no: int = 1,
        page_size: int = 50,
        **kwargs: Any,
    ) -> Any:
        """查询订单列表。"""
        body: dict[str, Any] = {"page_no": page_no, "page_size": page_size}
        if authorize_id is not None:
            body["authorize_id"] = authorize_id
        if order_status is not None:
            body["order_status"] = order_status
        if refund_status is not None:
            body["refund_status"] = refund_status
        if pay_time is not None:
            body["pay_time"] = pay_time
        if update_time is not None:
            body["update_time"] = update_time
        body.update(kwargs)
        return await self.request("/api/open/order/list", body)

    async def get_order_detail(self, order_no: str) -> Any:
        """查询订单详情。"""
        return await self.request("/api/open/order/detail", {"order_no": order_no})

    async def get_order_cards(self, order_no: str) -> Any:
        """查询订单卡密列表。"""
        return await self.request("/api/open/order/kam/list", {"order_no": order_no})

    async def ship_order(
        self,
        order_no: str,
        waybill_no: str,
        express_code: str,
        express_name: str,
        *,
        ship_name: str | None = None,
        ship_mobile: str | None = None,
        ship_district_id: int | None = None,
        ship_prov_name: str | None = None,
        ship_city_name: str | None = None,
        ship_area_name: str | None = None,
        ship_address: str | None = None,
    ) -> Any:
        """订单物流发货。"""
        body: dict[str, Any] = {
            "order_no": order_no,
            "waybill_no": waybill_no,
            "express_code": express_code,
            "express_name": express_name,
        }
        for key in (
            "ship_name",
            "ship_mobile",
            "ship_district_id",
            "ship_prov_name",
            "ship_city_name",
            "ship_area_name",
            "ship_address",
        ):
            val = locals()[key]
            if val is not None:
                body[key] = val
        return await self.request("/api/open/order/ship", body)

    async def modify_order_price(self, order_data: dict[str, Any]) -> Any:
        """订单修改价格。"""
        return await self.request("/api/open/order/modify/price", order_data)

    # ==================================================================
    # 其他
    # ==================================================================

    async def get_express_companies(self) -> Any:
        """查询快递公司列表。"""
        return await self.request("/api/open/express/companies")
