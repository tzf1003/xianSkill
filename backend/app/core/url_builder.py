from __future__ import annotations

from app.core.config import settings


def get_frontend_base_url() -> str:
    return (settings.FRONTEND_BASE_URL or settings.BASE_URL or "").rstrip("/")


def build_token_url(token_value: str) -> str:
    base_url = get_frontend_base_url()
    if not base_url:
        return f"/s/{token_value}"
    return f"{base_url}/s/{token_value}"