from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.schemas import ApiResponse
from app.core.config import settings
from app.core.deps import create_admin_token

auth_router = APIRouter(prefix="/v1/admin", tags=["admin-auth"])


class _LoginIn(BaseModel):
    username: str
    password: str


@auth_router.post("/login")
async def admin_login(body: _LoginIn) -> ApiResponse:
    if body.username != settings.ADMIN_USERNAME or body.password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="账号或密码错误")
    return ApiResponse(data={"token": create_admin_token()})