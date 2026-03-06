# M3 API — curl 使用示例

> 替换 `BASE_URL`、`SKILL_ID`、`SKU_ID`、`ORDER_ID`、`TOKEN`、`JOB_ID` 为实际值。

```bash
BASE_URL="http://localhost:8000"
```

---

## 1. 创建人工协助 SKU

```bash
# 先确保有一个 Skill
curl -s -X POST "$BASE_URL/v1/admin/skills" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "人工照片修复",
    "description": "由专业修图师手动处理您的老照片",
    "type": "prompt"
  }' | python -m json.tool

# 用返回的 skill id 创建 human SKU
SKILL_ID="<上面返回的 id>"
curl -s -X POST "$BASE_URL/v1/admin/skus" \
  -H "Content-Type: application/json" \
  -d "{
    \"skill_id\": \"$SKILL_ID\",
    \"name\": \"人工修复标准版\",
    \"price_cents\": 2900,
    \"delivery_mode\": \"human\",
    \"total_uses\": 1,
    \"human_sla_hours\": 24,
    \"human_price_cents\": 2900
  }" | python -m json.tool
```

---

## 2. 注册 Webhook（订单付款通知）

```bash
curl -s -X POST "$BASE_URL/v1/admin/webhooks" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-server.example.com/hooks/order-paid",
    "secret": "my-hmac-secret-key-change-me",
    "events": ["order.paid"],
    "description": "订单付款后通知运营"
  }' | python -m json.tool

# 查看所有 webhook（secret 不回显）
curl -s "$BASE_URL/v1/admin/webhooks" | python -m json.tool

# 禁用某个 webhook
WEBHOOK_ID="<webhook_id>"
curl -s -X POST "$BASE_URL/v1/admin/webhooks/$WEBHOOK_ID/disable" | python -m json.tool

# 删除 webhook
curl -s -X DELETE "$BASE_URL/v1/admin/webhooks/$WEBHOOK_ID" | python -m json.tool
```

### Webhook 推送格式

```json
{
  "event": "order.paid",
  "order_id": "uuid",
  "token_url": "http://localhost:8000/s/<token>",
  "sku": {
    "id": "uuid",
    "name": "人工修复标准版",
    "delivery_mode": "human",
    "human_sla_hours": 24
  },
  "skill": {
    "id": "uuid",
    "name": "人工照片修复",
    "type": "prompt"
  }
}
```

**签名验证（Python）**：
```python
import hashlib, hmac, json

def verify_signature(secret: str, body: bytes, sig_header: str) -> bool:
    expected = "sha256=" + hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, sig_header)

# sig_header = request.headers.get("X-Signature-SHA256")
```

---

## 3. 创建订单（触发 Webhook）

```bash
SKU_ID="<sku_id>"
curl -s -X POST "$BASE_URL/v1/admin/orders" \
  -H "Content-Type: application/json" \
  -d "{
    \"sku_id\": \"$SKU_ID\",
    \"channel\": \"wechat\"
  }" | python -m json.tool
# 返回：token_url = "/s/<token_value>"
# 同时向所有启用的 webhook 发送 order.paid 事件
```

---

## 4. 用户端流程（public API）

```bash
TOKEN="<token_value>"

# 获取 token 信息（含 delivery_mode、SLA、最新 job 状态）
curl -s "$BASE_URL/v1/public/token/$TOKEN" | python -m json.tool

# 上传需求材料（图片）
curl -s -X POST "$BASE_URL/v1/public/upload" \
  -F "token=$TOKEN" \
  -F "file=@/path/to/photo.jpg" | python -m json.tool
# 返回 object_key

# 提交 Job（human 模式不入队 worker，等待人工处理）
OBJECT_KEY="<object_key>"
curl -s -X POST "$BASE_URL/v1/public/job" \
  -H "Content-Type: application/json" \
  -d "{\"token\": \"$TOKEN\", \"inputs\": {\"image_key\": \"$OBJECT_KEY\"}}" \
  | python -m json.tool
# 返回 job_id，status = "queued"

# 轮询 Job 状态（等待人工交付）
JOB_ID="<job_id>"
curl -s "$BASE_URL/v1/public/job/$JOB_ID" | python -m json.tool
```

---

## 5. 管理员人工交付

```bash
JOB_ID="<job_id>"

# 上传交付产物，标记 Job succeeded，记录审计信息
curl -s -X POST "$BASE_URL/v1/admin/jobs/$JOB_ID/human-deliver" \
  -F "operator=张三" \
  -F "notes=已完成手动修复，色彩修正+噪点去除" \
  -F "file=@/path/to/restored_photo.jpg" \
  | python -m json.tool

# 查看交付审计记录
curl -s "$BASE_URL/v1/admin/jobs/$JOB_ID/delivery-record" | python -m json.tool
```

### 响应示例（delivery-record）

```json
{
  "code": 0,
  "data": {
    "id": "...",
    "job_id": "...",
    "operator": "张三",
    "notes": "已完成手动修复，色彩修正+噪点去除",
    "output_hash": "sha256-of-delivered-file",
    "created_at": "2026-03-06T10:30:00Z"
  }
}
```

---

## 6. 管理端查询

```bash
# 查看所有 human-mode 的待处理 Job（status=queued）
curl -s "$BASE_URL/v1/admin/jobs?status=queued" | python -m json.tool

# 查看某订单详情（含 token_url）
ORDER_ID="<order_id>"
curl -s "$BASE_URL/v1/admin/orders/$ORDER_ID" | python -m json.tool

# SKU 更新 SLA
SKU_ID="<sku_id>"
curl -s -X PUT "$BASE_URL/v1/admin/skus/$SKU_ID" \
  -H "Content-Type: application/json" \
  -d '{"human_sla_hours": 48}' | python -m json.tool
```

---

## 7. 完整状态流转

```
订单创建
  └─ Webhook 触发: order.paid → 运营人员收到通知
      └─ 发送 token_url 给用户

用户访问 token 页面
  └─ 看到 "人工处理" 标识 + SLA 说明
  └─ 上传需求材料 → 提交 Job (status=queued)
      └─ 不入 worker 队列

管理员
  └─ GET /v1/admin/jobs?status=queued 看到待处理
  └─ 下载用户输入（job.inputs.image_key）
  └─ 人工处理完成
  └─ POST /v1/admin/jobs/{id}/human-deliver
      └─ 上传产物 → Job status=succeeded → Token finalize
      └─ DeliveryRecord 记录操作人+hash（审计）

用户刷新 token 页面
  └─ GET /v1/public/token/{token} → latest_job.status=succeeded
  └─ 显示 "✅ 人工交付完成" + 下载链接
```
