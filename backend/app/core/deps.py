from __future__ import annotations

import base64
import hashlib
import hmac
import time
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from rq import Queue
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.config import settings
from app.infra.queue import get_queue as _get_queue
from app.infra.storage import StorageService, get_storage as _get_storage

# ── Session token (HMAC-SHA256, no extra deps) ───────────────────────

_TOKEN_TTL = 86400 * 7  # 7 天


def create_admin_token() -> str:
    """签发一个 7 天有效的管理员 session token。"""
    exp = int(time.time()) + _TOKEN_TTL
    payload = base64.urlsafe_b64encode(
        f"{settings.ADMIN_USERNAME}:{exp}".encode()
    ).decode()
    sig = hmac.new(
        settings.ADMIN_SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}.{sig}"


def _verify_admin_token(token: str) -> bool:
    """校验 HMAC 签名及有效期。"""
    try:
        payload_b64, sig = token.rsplit(".", 1)
        expected = hmac.new(
            settings.ADMIN_SECRET_KEY.encode(),
            payload_b64.encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return False
        payload = base64.urlsafe_b64decode(payload_b64 + "==").decode()
        _, exp_str = payload.rsplit(":", 1)
        return int(time.time()) < int(exp_str)
    except Exception:
        return False


_bearer = HTTPBearer(auto_error=False)


def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> None:
    """路由依赖：校验管理员 Bearer token，失败则 401。"""
    token = credentials.credentials if credentials else None
    if not token or not _verify_admin_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录或 Token 已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── DB / Queue / Storage ─────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """每次请求获取一个数据库会话，结束后自动关闭。"""
    async with async_session_factory() as session:
        yield session


def get_queue() -> Queue:
    return _get_queue()


def get_storage() -> StorageService:
    return _get_storage()


DbSession = Annotated[AsyncSession, Depends(get_db)]


