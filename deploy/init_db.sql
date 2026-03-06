-- M1 core tables init script (run via docker exec or psql)
-- Compatible with Postgres 16

-- Enums
DO $$ BEGIN
  CREATE TYPE skill_type AS ENUM ('prompt','external_service','workflow','client_exec');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE delivery_mode AS ENUM ('auto','human');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE order_status AS ENUM ('pending','paid','canceled');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE token_status AS ENUM ('active','expired','revoked');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE job_status AS ENUM ('queued','running','succeeded','failed','canceled');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- skills
CREATE TABLE IF NOT EXISTS skills (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name         VARCHAR(200) NOT NULL,
  description  TEXT,
  type         skill_type NOT NULL,
  version      VARCHAR(50) NOT NULL DEFAULT '1.0.0',
  input_schema JSONB,
  output_schema JSONB,
  enabled      BOOLEAN NOT NULL DEFAULT TRUE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- skus
CREATE TABLE IF NOT EXISTS skus (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  skill_id      UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
  name          VARCHAR(200) NOT NULL,
  price_cents   INTEGER NOT NULL DEFAULT 0,
  delivery_mode delivery_mode NOT NULL DEFAULT 'auto',
  total_uses    INTEGER NOT NULL DEFAULT 1,
  enabled       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_skus_skill_id ON skus(skill_id);

-- orders
CREATE TABLE IF NOT EXISTS orders (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  sku_id     UUID NOT NULL REFERENCES skus(id) ON DELETE CASCADE,
  status     order_status NOT NULL DEFAULT 'paid',
  channel    VARCHAR(100),
  metadata   JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_orders_sku_id ON orders(sku_id);

-- tokens
CREATE TABLE IF NOT EXISTS tokens (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  token          VARCHAR(64) UNIQUE NOT NULL,
  order_id       UUID UNIQUE NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  sku_id         UUID NOT NULL,
  skill_id       UUID NOT NULL,
  status         token_status NOT NULL DEFAULT 'active',
  total_uses     INTEGER NOT NULL,
  used_count     INTEGER NOT NULL DEFAULT 0,
  reserved_count INTEGER NOT NULL DEFAULT 0,
  expires_at     TIMESTAMPTZ,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_tokens_token    ON tokens(token);
CREATE INDEX IF NOT EXISTS ix_tokens_sku_id   ON tokens(sku_id);
CREATE INDEX IF NOT EXISTS ix_tokens_skill_id ON tokens(skill_id);

-- jobs
CREATE TABLE IF NOT EXISTS jobs (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  token_id         UUID NOT NULL REFERENCES tokens(id) ON DELETE CASCADE,
  skill_id         UUID NOT NULL,
  status           job_status NOT NULL DEFAULT 'queued',
  idempotency_key  VARCHAR(128),
  inputs           JSONB,
  result           JSONB,
  error            TEXT,
  started_at       TIMESTAMPTZ,
  finished_at      TIMESTAMPTZ,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_jobs_token_id   ON jobs(token_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_jobs_idempotency ON jobs(token_id, idempotency_key) WHERE idempotency_key IS NOT NULL;

-- assets
CREATE TABLE IF NOT EXISTS assets (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id       UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  filename     VARCHAR(500) NOT NULL,
  storage_key  VARCHAR(500) NOT NULL,
  content_type VARCHAR(200),
  size_bytes   INTEGER,
  hash         VARCHAR(128),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_assets_job_id ON assets(job_id);

-- Alembic version tracking (mark migration as done)
CREATE TABLE IF NOT EXISTS alembic_version (
  version_num VARCHAR(32) PRIMARY KEY
);
INSERT INTO alembic_version(version_num) VALUES ('0001_m1_core_tables')
  ON CONFLICT DO NOTHING;
