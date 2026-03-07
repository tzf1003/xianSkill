"""闲管家 API 基础客户端 — 封装签名、请求、异常处理等公共逻辑。"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class XGJApiError(Exception):
    """闲管家 API 返回业务错误。"""

    def __init__(self, code: int, msg: str, data: Any = None):
        self.code = code
        self.msg = msg
        self.data = data
        super().__init__(f"[XGJ Error {code}] {msg}")


class XGJBaseClient:
    """
    公共基类，子类只需覆盖 ``_build_sign`` 和 ``_build_url`` 即可支持不同签名模式。

    两种应用类型的差异仅在签名拼接顺序和 URL query 参数上，
    HTTP 层 (POST + JSON body) 完全一致。
    """

    BASE_URL: str  # 由子类指定

    def __init__(self, app_key: str, app_secret: str, *, timeout: float = 30.0):
        self.app_key = app_key
        self.app_secret = app_secret
        self._client = httpx.AsyncClient(timeout=timeout)

    # ------------------------------------------------------------------
    # 签名 & 请求（子类可覆盖）
    # ------------------------------------------------------------------

    @staticmethod
    def _md5(text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _serialize_body(self, data: dict[str, Any] | None) -> str:
        """将 body 序列化为紧凑 JSON（无空格），空字典序列化为 ``{}``。"""
        if not data:
            return "{}"
        return json.dumps(data, separators=(",", ":"), ensure_ascii=False)

    def _build_sign(self, body_json: str, timestamp: int) -> str:
        """由子类实现：根据应用类型生成签名。"""
        raise NotImplementedError

    def _build_url(self, path: str, timestamp: int, sign: str) -> str:
        """由子类实现：拼接完整请求 URL。"""
        raise NotImplementedError

    async def request(
        self,
        path: str,
        data: dict[str, Any] | None = None,
    ) -> Any:
        """
        发起签名请求并返回 ``data`` 字段。

        Raises:
            XGJApiError: 当 ``code != 0`` 时。
            httpx.HTTPStatusError: 当 HTTP 状态码异常时。
        """
        body_json = self._serialize_body(data)
        timestamp = int(time.time())
        sign = self._build_sign(body_json, timestamp)
        url = self._build_url(path, timestamp, sign)

        logger.debug("XGJ request: POST %s body=%s", url, body_json)

        resp = await self._client.post(
            url,
            content=body_json,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()

        result = resp.json()
        code = result.get("code")
        msg = result.get("msg", "")
        resp_data = result.get("data")

        if code != 0:
            raise XGJApiError(code, msg, resp_data)

        return resp_data

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "XGJBaseClient":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()
