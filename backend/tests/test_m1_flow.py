"""M1 集成测试 — 全链路：skill → sku → order(+token) → submit job → 幂等 → finalize。"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_flow(client: AsyncClient):
    """创建 skill+sku+order+token，提交 job，幂等重复提交不重复扣次，finalize。"""

    # 1. 创建 Skill
    resp = await client.post("/v1/admin/skills", json={
        "name": "老照片修复",
        "type": "prompt",
        "description": "AI 修复老旧照片",
    })
    assert resp.status_code == 200
    skill_data = resp.json()["data"]
    skill_id = skill_data["id"]
    assert skill_data["name"] == "老照片修复"

    # 2. 创建 SKU（3 次使用）
    resp = await client.post("/v1/admin/skus", json={
        "skill_id": skill_id,
        "name": "老照片修复-基础版",
        "price_cents": 999,
        "total_uses": 3,
    })
    assert resp.status_code == 200
    sku_data = resp.json()["data"]
    sku_id = sku_data["id"]
    assert sku_data["total_uses"] == 3

    # 3. 创建订单（自动生成 token）
    resp = await client.post("/v1/admin/orders", json={
        "sku_id": sku_id,
        "channel": "xianyu",
    })
    assert resp.status_code == 200
    order_data = resp.json()["data"]
    assert order_data["token_url"] is not None
    token_url = order_data["token_url"]
    token_value = token_url.split("/")[-1]

    # 4. 查询 token 信息
    resp = await client.get(f"/v1/public/token/{token_value}")
    assert resp.status_code == 200
    token_info = resp.json()["data"]
    assert token_info["remaining"] == 3
    assert token_info["total_uses"] == 3
    assert token_info["status"] == "active"
    assert token_info["skill"]["name"] == "老照片修复"

    # 5. 提交 Job（带 idempotency_key）
    resp = await client.post("/v1/public/job", json={
        "token": token_value,
        "idempotency_key": "req-001",
        "inputs": {"image_url": "https://example.com/photo.jpg"},
    })
    assert resp.status_code == 200
    job_data = resp.json()["data"]
    job_id = job_data["id"]
    assert job_data["status"] == "queued"

    # 6. 验证 token remaining 减少（reserve 冻结了 1 次）
    resp = await client.get(f"/v1/public/token/{token_value}")
    assert resp.json()["data"]["remaining"] == 2

    # 7. 幂等重复提交 — 不应重复扣次
    resp = await client.post("/v1/public/job", json={
        "token": token_value,
        "idempotency_key": "req-001",
        "inputs": {"image_url": "https://example.com/photo.jpg"},
    })
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == job_id  # 同一个 job

    # remaining 不变
    resp = await client.get(f"/v1/public/token/{token_value}")
    assert resp.json()["data"]["remaining"] == 2

    # 8. 查询 Job 状态
    resp = await client.get(f"/v1/public/job/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "queued"

    # 9. Finalize（成功）
    resp = await client.post(f"/v1/admin/jobs/{job_id}/finalize?success=true")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "succeeded"

    # 10. 验证 token：used=1, reserved=0, remaining=2
    resp = await client.get(f"/v1/public/token/{token_value}")
    token_after = resp.json()["data"]
    assert token_after["remaining"] == 2


@pytest.mark.asyncio
async def test_token_not_found(client: AsyncClient):
    resp = await client.get("/v1/public/token/nonexistent-token")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_submit_job_invalid_token(client: AsyncClient):
    resp = await client.post("/v1/public/job", json={
        "token": "nonexistent",
    })
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_finalize_already_finalized(client: AsyncClient):
    """连续 finalize 同一 job 应返回 409。"""
    # 快速创建 skill → sku → order → job
    resp = await client.post("/v1/admin/skills", json={"name": "s", "type": "prompt"})
    skill_id = resp.json()["data"]["id"]

    resp = await client.post("/v1/admin/skus", json={"skill_id": skill_id, "name": "k", "total_uses": 5})
    sku_id = resp.json()["data"]["id"]

    resp = await client.post("/v1/admin/orders", json={"sku_id": sku_id})
    token_value = resp.json()["data"]["token_url"].split("/")[-1]

    resp = await client.post("/v1/public/job", json={"token": token_value})
    job_id = resp.json()["data"]["id"]

    # 第一次 finalize
    resp = await client.post(f"/v1/admin/jobs/{job_id}/finalize?success=true")
    assert resp.status_code == 200

    # 第二次 finalize — 应返回 409
    resp = await client.post(f"/v1/admin/jobs/{job_id}/finalize?success=true")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_exhaust_token_uses(client: AsyncClient):
    """用完所有次数后，提交应被拒绝。"""
    resp = await client.post("/v1/admin/skills", json={"name": "x", "type": "prompt"})
    skill_id = resp.json()["data"]["id"]

    resp = await client.post("/v1/admin/skus", json={"skill_id": skill_id, "name": "k", "total_uses": 1})
    sku_id = resp.json()["data"]["id"]

    resp = await client.post("/v1/admin/orders", json={"sku_id": sku_id})
    token_value = resp.json()["data"]["token_url"].split("/")[-1]

    # 第一次提交 — 成功
    resp = await client.post("/v1/public/job", json={"token": token_value})
    assert resp.status_code == 200

    # 第二次提交 — 次数用完（reserve 后 remaining=0）
    resp = await client.post("/v1/public/job", json={"token": token_value})
    assert resp.status_code == 403
