from __future__ import annotations

import enum
from dataclasses import asdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx

from app.core.config import settings

if TYPE_CHECKING:
    from app.domain.models import AIProvider, Project


class AIProtocol(str, enum.Enum):
    openai = "openai"
    anthropic = "anthropic"
    gemini = "gemini"
    volcengine = "volcengine"


@dataclass
class AIRuntimeConfig:
    protocol: str
    model: str
    api_key: str
    base_url: str | None = None
    provider_id: str | None = None
    provider_name: str | None = None
    source: str = "env"

    def to_log_dict(self) -> dict[str, Any]:
        return {
            "protocol": self.protocol,
            "model": self.model,
            "base_url": self.base_url,
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "source": self.source,
        }

    def to_runtime_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AIRuntimeConfig":
        return cls(
            protocol=str(payload.get("protocol") or "").strip(),
            model=str(payload.get("model") or "").strip(),
            api_key=str(payload.get("api_key") or "").strip(),
            base_url=(str(payload.get("base_url") or "").strip() or None),
            provider_id=(str(payload.get("provider_id") or "").strip() or None),
            provider_name=(str(payload.get("provider_name") or "").strip() or None),
            source=str(payload.get("source") or "env").strip() or "env",
        )


def normalize_protocol(value: str | AIProtocol | None) -> str:
    if isinstance(value, AIProtocol):
        return value.value
    text = (value or AIProtocol.gemini.value).strip().lower()
    if text not in {AIProtocol.openai.value, AIProtocol.anthropic.value, AIProtocol.gemini.value, AIProtocol.volcengine.value}:
        raise ValueError(f"不支持的 AI 协议: {value}")
    return text


def mask_api_key(api_key: str | None) -> str | None:
    if not api_key:
        return None
    trimmed = api_key.strip()
    if len(trimmed) <= 8:
        return "*" * len(trimmed)
    return f"{trimmed[:4]}...{trimmed[-4:]}"


def sanitize_model_entries(raw_models: Any) -> list[dict[str, str]]:
    if not raw_models:
        return []

    items: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in raw_models:
        model_id = ""
        label = ""

        if isinstance(raw, str):
            model_id = raw.strip()
        elif isinstance(raw, dict):
            model_id = str(raw.get("id") or raw.get("name") or "").strip()
            label = str(raw.get("label") or raw.get("display_name") or raw.get("displayName") or "").strip()

        if not model_id or model_id in seen:
            continue

        seen.add(model_id)
        item = {"id": model_id}
        if label and label != model_id:
            item["label"] = label
        items.append(item)

    return items


def current_env_runtime_config() -> AIRuntimeConfig:
    protocol = normalize_protocol(settings.AI_API_FORMAT)
    if protocol == AIProtocol.openai.value:
        return AIRuntimeConfig(
            protocol=protocol,
            model=settings.OPENAI_IMAGE_MODEL,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            provider_name="env:openai",
        )
    if protocol == AIProtocol.anthropic.value:
        return AIRuntimeConfig(
            protocol=protocol,
            model=settings.ANTHROPIC_IMAGE_MODEL,
            api_key=settings.ANTHROPIC_API_KEY,
            base_url=settings.ANTHROPIC_BASE_URL,
            provider_name="env:anthropic",
        )
    if protocol == AIProtocol.volcengine.value:
        return AIRuntimeConfig(
            protocol=protocol,
            model=settings.VOLCENGINE_IMAGE_MODEL,
            api_key=settings.VOLCENGINE_API_KEY,
            base_url=settings.VOLCENGINE_BASE_URL,
            provider_name="env:volcengine",
        )
    return AIRuntimeConfig(
        protocol=AIProtocol.gemini.value,
        model=settings.GEMINI_IMAGE_MODEL,
        api_key=settings.GEMINI_API_KEY,
        base_url=settings.GEMINI_BASE_URL,
        provider_name="env:gemini",
    )


def build_project_runtime_config(project: Project | None) -> AIRuntimeConfig | None:
    if not project or not project.ai_provider_id or not project.ai_model:
        return None

    provider: AIProvider | None = getattr(project, "ai_provider", None)
    if provider is None:
        raise RuntimeError("项目绑定的 AI 服务商不存在或已被删除")
    if not provider.enabled:
        raise RuntimeError("项目绑定的 AI 服务商已禁用")

    protocol = normalize_protocol(getattr(provider, "protocol", None))
    return AIRuntimeConfig(
        protocol=protocol,
        model=project.ai_model,
        api_key=(provider.api_key or "").strip(),
        base_url=(provider.base_url or "").strip() or None,
        provider_id=str(provider.id),
        provider_name=provider.name,
        source="project",
    )


async def fetch_remote_models(protocol: str | AIProtocol, base_url: str | None, api_key: str) -> list[dict[str, str]]:
    normalized = normalize_protocol(protocol)
    key = (api_key or "").strip()
    if not key:
        raise RuntimeError("缺少 API Key，无法获取模型列表")

    timeout = httpx.Timeout(20.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        if normalized == AIProtocol.openai.value:
            return await _fetch_openai_models(client, base_url, key)
        if normalized == AIProtocol.anthropic.value:
            return await _fetch_anthropic_models(client, base_url, key)
        if normalized == AIProtocol.volcengine.value:
            return await _fetch_volcengine_models(client, base_url, key)
        return await _fetch_gemini_models(client, base_url, key)


def _join_api_url(base_url: str, api_path: str) -> str:
    base = (base_url or "").rstrip("/")
    path = api_path if api_path.startswith("/") else f"/{api_path}"

    if not base:
        return path
    if base.endswith("/v1") and path.startswith("/v1/"):
        return base + path[3:]
    if base.endswith("/v1beta") and path.startswith("/v1beta/"):
        return base + path[7:]
    return base + path


async def _fetch_openai_models(client: httpx.AsyncClient, base_url: str | None, api_key: str) -> list[dict[str, str]]:
    url = _join_api_url(base_url or settings.OPENAI_BASE_URL, "/models")
    response = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
    _raise_for_status(response, "获取 OpenAI 模型列表失败")
    payload = response.json()
    return sanitize_model_entries(payload.get("data", []))


async def _fetch_anthropic_models(client: httpx.AsyncClient, base_url: str | None, api_key: str) -> list[dict[str, str]]:
    url = _join_api_url(base_url or settings.ANTHROPIC_BASE_URL or "https://api.anthropic.com", "/v1/models")
    response = await client.get(
        url,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )
    _raise_for_status(response, "获取 Anthropic 模型列表失败")
    payload = response.json()
    return sanitize_model_entries(payload.get("data") or payload.get("models") or [])


async def _fetch_gemini_models(client: httpx.AsyncClient, base_url: str | None, api_key: str) -> list[dict[str, str]]:
    url = _join_api_url(base_url or settings.GEMINI_BASE_URL, "/v1beta/models")
    response = await client.get(url, params={"key": api_key})
    _raise_for_status(response, "获取 Gemini 模型列表失败")
    payload = response.json()

    models: list[dict[str, str]] = []
    for item in payload.get("models", []):
        methods = item.get("supportedGenerationMethods") or []
        if methods and "generateContent" not in methods:
            continue
        name = str(item.get("name") or "").strip()
        model_id = name.removeprefix("models/") if name.startswith("models/") else name
        if not model_id:
            continue
        entry: dict[str, str] = {"id": model_id}
        display_name = str(item.get("displayName") or "").strip()
        if display_name and display_name != model_id:
            entry["label"] = display_name
        models.append(entry)
    return sanitize_model_entries(models)


async def _fetch_volcengine_models(client: httpx.AsyncClient, base_url: str | None, api_key: str) -> list[dict[str, str]]:
    url = _join_api_url(base_url or settings.VOLCENGINE_BASE_URL, "/models")
    try:
        response = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
        if response.is_success:
            payload = response.json()
            models = sanitize_model_entries(payload.get("data", []))
            if models:
                return models
    except Exception:
        pass

    doc_response = await client.get("https://www.volcengine.com/docs/82379/1330310")
    _raise_for_status(doc_response, "获取火山方舟模型列表失败")
    text = doc_response.text

    import re

    candidates = re.findall(r"\b(?:doubao|deepseek|glm|kimi)-[a-z0-9-]+\b", text, flags=re.IGNORECASE)
    models = sanitize_model_entries(candidates)
    if not models:
        raise RuntimeError("火山方舟模型列表解析失败")
    return models


def _raise_for_status(response: httpx.Response, message: str) -> None:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        text = exc.response.text[:300]
        raise RuntimeError(f"{message}: HTTP {exc.response.status_code} {text}") from exc