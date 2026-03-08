"""Token 与计次服务。

遵循 AGENT.md §6 Token 安全与计次规则：
- token >= 128-bit 随机，URL-safe
- scope 校验：绑定 sku_id/skill_id
- 两阶段计次：reserve（冻结）/ finalize（确认或返还）
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Token, TokenStatus


def generate_token() -> str:
    """生成 >= 128-bit 随机 URL-safe token（32 字节 = 256-bit）。"""
    return secrets.token_urlsafe(32)


async def create_token(
    session: AsyncSession,
    *,
    order_id: uuid.UUID,
    sku_id: uuid.UUID,
    skill_id: uuid.UUID,
    total_uses: int,
    expires_at: datetime | None = None,
) -> Token:
    """为订单创建交付 token。"""
    token = Token(
        token=generate_token(),
        order_id=order_id,
        sku_id=sku_id,
        skill_id=skill_id,
        total_uses=total_uses,
        expires_at=expires_at,
    )
    session.add(token)
    return token


async def get_token_by_value(session: AsyncSession, token_value: str) -> Token | None:
    """通过 token 字符串查找 Token 记录。"""
    stmt = select(Token).where(Token.token == token_value)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def validate_token_usable(token: Token) -> None:
    """校验 token 是否可用（状态 + 过期 + 余量）。"""
    if token.status != TokenStatus.active:
        raise HTTPException(status_code=403, detail=f"Token status is {token.status.value}")
    if token.expires_at and token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=403, detail="Token has expired")
    if token.remaining <= 0:
        raise HTTPException(status_code=403, detail="Token has no remaining uses")


def validate_scope(token: Token, skill_id: uuid.UUID | None = None) -> None:
    """scope 校验：token 绑定的 skill_id 必须匹配。"""
    if skill_id and token.skill_id != skill_id:
        raise HTTPException(status_code=403, detail="Token scope mismatch: skill_id does not match")


def reserve(token: Token) -> None:
    """预扣一次（冻结），submit_job 时调用。"""
    if token.remaining <= 0:
        raise HTTPException(status_code=403, detail="Token has no remaining uses")
    token.reserved_count += 1


def finalize_success(token: Token) -> None:
    """Job 成功，确认扣除：reserved_count -1，used_count +1。"""
    if token.reserved_count <= 0:
        raise HTTPException(status_code=409, detail="No reserved count to finalize")
    token.reserved_count -= 1
    token.used_count += 1


def finalize_failure(token: Token) -> None:
    """Job 失败，返还：reserved_count -1。"""
    if token.reserved_count <= 0:
        raise HTTPException(status_code=409, detail="No reserved count to release")
    token.reserved_count -= 1


def grant_uses(token: Token, uses: int) -> None:
    """给 token 增加可用总次数。"""
    if uses <= 0:
        return
    token.total_uses += uses
