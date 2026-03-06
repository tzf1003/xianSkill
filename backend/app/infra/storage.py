"""MinIO 对象存储封装，提供 put/get/presigned URL 操作。"""

from __future__ import annotations

import io
from datetime import timedelta

from minio import Minio

from app.core.config import settings


class StorageService:
    def __init__(self) -> None:
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self.bucket = settings.MINIO_BUCKET

    # ── 初始化 ────────────────────────────────────────────────────────
    def ensure_bucket(self) -> None:
        """如果 bucket 不存在则创建。"""
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    # ── 写入 ──────────────────────────────────────────────────────────
    def put_bytes(
        self,
        object_key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        self.client.put_object(
            self.bucket,
            object_key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )

    # ── 读取 ──────────────────────────────────────────────────────────
    def get_bytes(self, object_key: str) -> bytes:
        resp = self.client.get_object(self.bucket, object_key)
        try:
            return resp.read()
        finally:
            resp.close()

    # ── 预签名 URL ────────────────────────────────────────────────────
    def presigned_put_url(self, object_key: str, expires_seconds: int = 3600) -> str:
        return self.client.presigned_put_object(
            self.bucket,
            object_key,
            expires=timedelta(seconds=expires_seconds),
        )

    def presigned_get_url(self, object_key: str, expires_seconds: int = 3600) -> str:
        return self.client.presigned_get_object(
            self.bucket,
            object_key,
            expires=timedelta(seconds=expires_seconds),
        )


def get_storage() -> StorageService:
    """FastAPI / 任务中统一的 storage 工厂。"""
    return StorageService()
