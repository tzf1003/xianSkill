from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用全局配置，优先从环境变量读取。"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # --- App ---
    APP_NAME: str = "skill-platform"
    DEBUG: bool = False

    # --- Database (Postgres) ---
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:15432/skill_platform"

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6378/0"

    # --- MinIO / S3 ---
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "tzf1003"
    MINIO_SECRET_KEY: str = "zf123456"
    MINIO_BUCKET: str = "skill-assets"
    MINIO_SECURE: bool = False
    # 若设置，预签名 URL 的 http(s)://host:port 前缀将被替换为此值
    # 例如 /minio，配合前端反代使用
    MINIO_PUBLIC_BASE: str = ""

    # --- AI API 格式选择 ---
    # 可选值: gemini | openai | anthropic
    AI_API_FORMAT: str = "gemini"

    # --- Gemini ---
    GEMINI_API_KEY: str = ""
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com"
    GEMINI_IMAGE_MODEL: str = "gemini-2.0-flash-preview-image-generation"
    GEMINI_TEXT_MODEL: str = "gemini-2.0-flash"

    # --- OpenAI / OpenAI-Compatible ---
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_IMAGE_MODEL: str = "gpt-4o"
    OPENAI_TEXT_MODEL: str = "gpt-4o"

    # --- Anthropic / Anthropic-Compatible ---
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_BASE_URL: str = ""
    ANTHROPIC_IMAGE_MODEL: str = "claude-opus-4-5"
    ANTHROPIC_TEXT_MODEL: str = "claude-opus-4-5"

    # --- 闲管家开放平台（进销存/ERP）---
    XGJ_ERP_APP_KEY: str = ""
    XGJ_ERP_APP_SECRET: str = ""

    # --- 闲管家虚拟货源 ---
    XGJ_VIRTUAL_APP_KEY: str = ""
    XGJ_VIRTUAL_APP_SECRET: str = ""
    XGJ_VIRTUAL_MCH_ID: str = ""
    XGJ_VIRTUAL_MCH_SECRET: str = ""

    # --- 闲管家虚拟货源对外网关 ---
    # 外部可访问的网关根 URL，用于闲管家回调/设置货源地址
    # 解决内网部署 + 多层反代场景下闲管家找不到的问题
    XGJ_BASE_URL: str = ""

    # --- Webhook ---
    # 对外可访问的服务根 URL，用于生成 token_url 写入 webhook 通知
    BASE_URL: str = "http://localhost:8000"

    # --- Admin 登录 ---
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    # 用于 HMAC 签名 session token，生产环境请替换为随机长字符串
    ADMIN_SECRET_KEY: str = "change-this-secret-in-production"


settings = Settings()
