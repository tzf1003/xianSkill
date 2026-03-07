"""MinIO 对象存储封装，提供 put/get/presigned URL 操作。"""

from __future__ import annotations

import io
import json
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
        """如果 bucket 不存在则创建，并设置 goods/ 前缀公开读策略。"""
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)
        # 允许匿名读取 goods/ 前缀（用于 logo 等公开图片资源）
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{self.bucket}/goods/*"],
                }
            ],
        }
        self.client.set_bucket_policy(self.bucket, json.dumps(policy))

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
        # MinIO 预签名URL最大有效期为7天（604800秒）
        expires_seconds = min(expires_seconds, 604800)
        url = self.client.presigned_get_object(
            self.bucket,
            object_key,
            expires=timedelta(seconds=expires_seconds),
        )
        public_base = settings.MINIO_PUBLIC_BASE
        if public_base:
            # 将 http(s)://host:port 替换为公共前缀（如 /minio）
            import re
            url = re.sub(r'^https?://[^/]+', public_base.rstrip('/'), url)
        return url

    def public_url(self, object_key: str) -> str:
        """构造永久公开访问URL（需要 bucket 已设为公开或配置了 MINIO_PUBLIC_BASE）。"""
        public_base = settings.MINIO_PUBLIC_BASE
        if public_base:
            return f"{public_base.rstrip('/')}/{self.bucket}/{object_key}"
        # 回退：使用7天预签名URL
        return self.presigned_get_url(object_key, expires_seconds=604800)


def get_storage() -> StorageService:
    """FastAPI / 任务中统一的 storage 工厂。"""
    return StorageService()
