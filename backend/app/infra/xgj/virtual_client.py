"""
闲管家虚拟货源标准接口客户端。

虚拟货源模式中，**闲管家是调用方**，我们是货源服务商。
因此本模块提供：
  1. ``XGJVirtualClient``  — 签名验证 + 回调通知发送工具
  2. 用于 FastAPI 的请求签名校验辅助方法

签名规则（虚拟货源）：
    sign = md5("管家应用ID,管家对接密钥,md5(body),时间戳,货源商户ID,货源对接密钥")

请求 Query 参数（闲管家发起）：
    ?app_id={app_id}&mch_id={mch_id}&timestamp={ts}&sign={sign}

全局错误码：
    0   - 请求成功
    1   - 请求错误
    401 - 签名错误
    408 - 时间戳已超过有效期
    500 - 系统异常
    1000 - 商户不存在
    1001 - 商户不可用
    1002 - 商户余额不足
    1100 - 商品不存在
    1101 - 商品不可用
    1102 - 商品库存不足
    1200 - 订单不存在
    1201 - 下单参数错误
    1202 - 下单金额低于成本价
    1203 - 下单管家订单号已存在
    1209 - 下单超时
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# 签名有效期（秒），闲管家官方文档要求 5 分钟内有效
_SIGN_EXPIRE_SECONDS = 300


class XGJVirtualClient:
    """
    闲管家虚拟货源工具类。

    Parameters:
        app_id: 闲管家平台提供的应用 ID（对应管家后台「应用概况 → AppKey」）
        app_secret: 闲管家平台提供的应用密钥（对应管家后台「应用概况 → AppSecret」）
        mch_id: 货源方商户 ID（我方提供给闲管家的对接商户 ID）
        mch_secret: 货源方商户密钥（我方提供给闲管家的对接密钥）
    """

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        mch_id: str,
        mch_secret: str,
        *,
        timeout: float = 30.0,
    ):
        self.app_id = app_id
        self.app_secret = app_secret
        self.mch_id = mch_id
        self.mch_secret = mch_secret
        self._client = httpx.AsyncClient(timeout=timeout)

    # ------------------------------------------------------------------
    # 签名工具
    # ------------------------------------------------------------------

    @staticmethod
    def _md5(text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def generate_sign(self, body_json: str, timestamp: int) -> str:
        """
        按虚拟货源签名规则生成签名。

        拼接顺序：``管家应用ID,管家对接密钥,md5(body),时间戳,货源商户ID,货源对接密钥``
        """
        body_md5 = self._md5(body_json)
        raw = (
            f"{self.app_id},{self.app_secret},{body_md5},"
            f"{timestamp},{self.mch_id},{self.mch_secret}"
        )
        return self._md5(raw)

    def verify_sign(
        self,
        sign: str,
        body_json: str,
        timestamp: int,
        *,
        check_expire: bool = True,
    ) -> bool:
        """
        校验来自闲管家的请求签名。

        Args:
            sign: 请求中的 sign 参数
            body_json: 原始 body 字符串
            timestamp: 请求中的 timestamp 参数（秒）
            check_expire: 是否检查时间戳有效期（默认 5 分钟）

        Returns:
            签名是否合法
        """
        if check_expire and abs(int(time.time()) - timestamp) > _SIGN_EXPIRE_SECONDS:
            return False
        expected = self.generate_sign(body_json, timestamp)
        return expected == sign

    # ------------------------------------------------------------------
    # 标准响应构建
    # ------------------------------------------------------------------

    @staticmethod
    def ok_response(data: Any = None) -> dict[str, Any]:
        """构建成功响应体。"""
        return {"code": 0, "msg": "OK", "data": data or {}}

    @staticmethod
    def error_response(code: int, msg: str) -> dict[str, Any]:
        """构建错误响应体。"""
        return {"code": code, "msg": msg}

    # ------------------------------------------------------------------
    # 回调通知（货源方 → 闲管家）
    # ------------------------------------------------------------------

    def _serialize_body(self, data: dict[str, Any] | None) -> str:
        if not data:
            return "{}"
        return json.dumps(data, separators=(",", ":"), ensure_ascii=False)

    async def send_callback(self, notify_url: str, data: dict[str, Any]) -> Any:
        """
        向闲管家发送回调通知（商品变更 / 订单结果）。

        回调 URL 由闲管家在创建订单或订阅商品时传入。
        签名附加在 query 参数中。
        """
        body_json = self._serialize_body(data)
        timestamp = int(time.time())
        sign = self.generate_sign(body_json, timestamp)
        url = (
            f"{notify_url}?app_id={self.app_id}"
            f"&mch_id={self.mch_id}"
            f"&timestamp={timestamp}"
            f"&sign={sign}"
        )

        logger.debug("XGJ virtual callback: POST %s body=%s", url, body_json)

        resp = await self._client.post(
            url,
            content=body_json,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()

    async def notify_product_change(
        self,
        notify_url: str,
        goods_no: str,
        *,
        price: int | None = None,
        stock: int | None = None,
        status: int | None = None,
    ) -> Any:
        """发送商品变更回调通知。"""
        data: dict[str, Any] = {"goods_no": goods_no}
        if price is not None:
            data["price"] = price
        if stock is not None:
            data["stock"] = stock
        if status is not None:
            data["status"] = status
        return await self.send_callback(notify_url, data)

    async def notify_order_result(
        self,
        notify_url: str,
        order_data: dict[str, Any],
    ) -> Any:
        """发送订单结果回调通知。"""
        return await self.send_callback(notify_url, order_data)

    async def notify_coupon_change(
        self,
        notify_url: str,
        coupon_data: dict[str, Any],
    ) -> Any:
        """发送券码状态变更回调通知。"""
        return await self.send_callback(notify_url, coupon_data)

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "XGJVirtualClient":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()
