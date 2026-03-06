-- M3 Migration — 人工协助 SKU 业务闭环
-- 在 M1/M2 已运行的 Postgres 数据库上执行

BEGIN;

-- 1. SKU 扩展字段
ALTER TABLE skus
  ADD COLUMN IF NOT EXISTS human_sla_hours   INTEGER,
  ADD COLUMN IF NOT EXISTS human_price_cents INTEGER;

COMMENT ON COLUMN skus.human_sla_hours     IS '人工处理 SLA（小时），仅 delivery_mode=human 时有效';
COMMENT ON COLUMN skus.human_price_cents   IS '人工服务附加定价（分）';

-- 2. Webhook 配置表
CREATE TABLE IF NOT EXISTS webhooks (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  url         VARCHAR(2000) NOT NULL,
  secret      VARCHAR(500),
  events      JSONB,              -- null = 订阅全部事件
  description VARCHAR(500),
  enabled     BOOLEAN NOT NULL DEFAULT TRUE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  webhooks        IS 'Webhook 端点配置';
COMMENT ON COLUMN webhooks.secret IS 'HMAC-SHA256 签名密钥（不回显）';
COMMENT ON COLUMN webhooks.events IS '订阅事件列表，如 ["order.paid"]；null 表示订阅全部';

-- 3. 人工交付记录表（审计证据）
CREATE TABLE IF NOT EXISTS delivery_records (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id      UUID NOT NULL UNIQUE REFERENCES jobs(id) ON DELETE CASCADE,
  operator    VARCHAR(200) NOT NULL,
  notes       TEXT,
  output_hash VARCHAR(128),      -- SHA-256 of delivered file
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_delivery_records_job_id ON delivery_records (job_id);

COMMENT ON TABLE  delivery_records             IS '人工交付审计记录';
COMMENT ON COLUMN delivery_records.operator    IS '操作人姓名';
COMMENT ON COLUMN delivery_records.output_hash IS '交付产物 SHA-256 哈希';

COMMIT;
