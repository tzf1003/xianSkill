from __future__ import annotations

import base64
import io
import sys
import types

import pytest
from httpx import AsyncClient
from PIL import Image

from app.core.config import settings
from app.runners.providers.volcengine_provider import VolcengineProvider
from app.services.ai_provider_service import AIRuntimeConfig


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    resp = await client.post("/v1/admin/login", json={
        "username": settings.ADMIN_USERNAME,
        "password": settings.ADMIN_PASSWORD,
    })
    assert resp.status_code == 200
    token = resp.json()["data"]["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_admin_can_refresh_ai_provider_models(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    headers = await _admin_headers(client)

    create_resp = await client.post(
        "/v1/admin/ai-providers",
        json={
            "name": "OpenAI Proxy",
            "protocol": "openai",
            "base_url": "https://example.com/v1",
            "api_key": "sk-test-1234",
        },
        headers=headers,
    )
    assert create_resp.status_code == 200
    provider_id = create_resp.json()["data"]["id"]

    async def fake_fetch_remote_models(protocol: str, base_url: str | None, api_key: str):
        assert protocol == "openai"
        assert base_url == "https://example.com/v1"
        assert api_key == "sk-test-1234"
        return [{"id": "gpt-image-1", "label": "GPT Image 1"}, {"id": "gpt-4o"}]

    monkeypatch.setattr("app.api.admin.fetch_remote_models", fake_fetch_remote_models)

    refresh_resp = await client.post(f"/v1/admin/ai-providers/{provider_id}/refresh-models", headers=headers)
    assert refresh_resp.status_code == 200
    payload = refresh_resp.json()["data"]
    assert [item["id"] for item in payload["models"]] == ["gpt-image-1", "gpt-4o"]


@pytest.mark.asyncio
async def test_project_ai_model_must_exist_in_saved_provider_models(client: AsyncClient):
    headers = await _admin_headers(client)

    provider_resp = await client.post(
        "/v1/admin/ai-providers",
        json={
            "name": "Anthropic Proxy",
            "protocol": "anthropic",
            "api_key": "sk-ant-1234",
            "models": [{"id": "claude-3-7-sonnet"}],
        },
        headers=headers,
    )
    assert provider_resp.status_code == 200
    provider_id = provider_resp.json()["data"]["id"]

    skill_resp = await client.post(
        "/v1/admin/skills",
        json={"name": "图像修复", "type": "prompt"},
        headers=headers,
    )
    assert skill_resp.status_code == 200
    skill_id = skill_resp.json()["data"]["id"]

    bad_resp = await client.post(
        "/v1/admin/projects",
        json={
            "name": "测试项目",
            "slug": "test-project-ai-binding",
            "skill_id": skill_id,
            "ai_provider_id": provider_id,
            "ai_model": "not-exists-model",
        },
        headers=headers,
    )
    assert bad_resp.status_code == 400

    ok_resp = await client.post(
        "/v1/admin/projects",
        json={
            "name": "测试项目",
            "slug": "test-project-ai-binding-ok",
            "skill_id": skill_id,
            "ai_provider_id": provider_id,
            "ai_model": "claude-3-7-sonnet",
        },
        headers=headers,
    )
    assert ok_resp.status_code == 200
    data = ok_resp.json()["data"]
    assert data["ai_provider_id"] == provider_id
    assert data["ai_model"] == "claude-3-7-sonnet"


@pytest.mark.asyncio
async def test_admin_can_create_volcengine_ai_provider(client: AsyncClient):
    headers = await _admin_headers(client)

    resp = await client.post(
        "/v1/admin/ai-providers",
        json={
            "name": "火山方舟",
            "protocol": "volcengine",
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
            "api_key": "ark-test-1234",
            "models": [{"id": "doubao-seedream-3-0-t2i-250415"}],
        },
        headers=headers,
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["protocol"] == "volcengine"
    assert data["models"][0]["id"] == "doubao-seedream-3-0-t2i-250415"


def test_volcengine_provider_uses_ark_images_generate(monkeypatch: pytest.MonkeyPatch):
    raw_image = io.BytesIO()
    Image.new("RGB", (1200, 800), (255, 0, 0)).save(raw_image, format="PNG")
    source_bytes = raw_image.getvalue()
    encoded = base64.b64encode(source_bytes).decode("utf-8")

    captured: dict[str, object] = {}

    class FakeUsage:
        generated_images = 1
        output_tokens = 16
        total_tokens = 16

    class FakeImage:
        b64_json = encoded
        url = ""

    class FakeResponse:
        error = None
        data = [FakeImage()]
        usage = FakeUsage()

    class FakeImages:
        def generate(self, **kwargs):
            captured.update(kwargs)
            return FakeResponse()

    class FakeArk:
        def __init__(self, **kwargs):
            captured["client_kwargs"] = kwargs
            self.images = FakeImages()

    monkeypatch.setitem(sys.modules, "volcenginesdkarkruntime", types.SimpleNamespace(Ark=FakeArk))

    provider = VolcengineProvider(
        AIRuntimeConfig(
            protocol="volcengine",
            model="doubao-seededit-3-0-i2i",
            api_key="ark-test-key",
            base_url="https://ark.cn-beijing.volces.com/api/v3",
        )
    )

    result = provider.complete("test prompt", source_bytes)

    assert captured["client_kwargs"] == {
        "api_key": "ark-test-key",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "timeout": 600.0,
    }
    assert captured["response_format"] == "b64_json"
    assert captured["output_format"] == "png"
    assert captured["watermark"] is False
    assert captured["size"] == "2048x2048"
    assert isinstance(captured["image"], str)
    assert str(captured["image"]).startswith("data:image/png;base64,")
    assert result.output_image_bytes > 0
    assert result.extra["source"] == "b64_json"
    assert result.extra["request_size"] == "2048x2048"


def test_volcengine_provider_requires_new_ark_sdk(monkeypatch: pytest.MonkeyPatch):
    class FakeArk:
        def __init__(self, **kwargs):
            self.chat = object()

    monkeypatch.setitem(sys.modules, "volcenginesdkarkruntime", types.SimpleNamespace(Ark=FakeArk))

    provider = VolcengineProvider(
        AIRuntimeConfig(
            protocol="volcengine",
            model="doubao-seededit-3-0-i2i",
            api_key="ark-test-key",
            base_url="https://ark.cn-beijing.volces.com/api/v3",
        )
    )

    with pytest.raises(RuntimeError, match=r">=5,<6"):
        provider.complete("test prompt")