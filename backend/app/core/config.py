from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用全局配置，优先从环境变量读取。"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # --- App ---
    APP_NAME: str = "skill-platform"
    DEBUG: bool = False

    # --- Database (Postgres) ---
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/skill_platform"

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- MinIO / S3 ---
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "skill-assets"
    MINIO_SECURE: bool = False

    # --- Webhook ---
    # 对外可访问的服务根 URL，用于生成 token_url 写入 webhook 通知
    BASE_URL: str = "http://localhost:8000"


settings = Settings()
