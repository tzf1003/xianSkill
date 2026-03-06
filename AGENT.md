# AGENT.md — Skill 商品化与自动交付平台（轻量可扩展）

## 1. 项目目标（Goal）
构建一个前后端分离、轻量、可扩展的“Skill 上架与自动交付平台”：
- 用户侧：通过 token URL 访问某个 Skill 的交付页面，上传输入并获取结果。
- 商家侧：支持 SKU 售卖（自动交付 / 人工协助），订单触发生成 token 并发给用户。
- 扩展侧：同一框架下支持 图像类 Skill → 文本类 → 外部服务类 → Workflow（多步骤编排）→ 用户端执行类 → AI 客服辅助。

## 2. 非目标（Non-Goal）
- 不做复杂多商户体系、复杂营销体系。
- 不实现静默安装、隐藏控制或持久化的用户端程序。
- 不提供任意命令执行通道：用户端执行必须 allowlist + 模板约束，并可审计。

## 3. 核心概念（Domain Model）
统一以“能力 = Skill，可售卖 = SKU，可交付 = Token + Job”表达：

- Skill：能力定义（输入输出 schema、运行方式 runner、版本）。
- SKU：售卖单元（价格、交付模式 auto/human、次数、SLA、可选服务）。
- Order：订单（来自渠道/后台录入；绑定 SKU）。
- Token：交付凭证（随机强 token；scope 限制；计次；过期；撤销）。
- Job：一次执行（异步任务；可重试；可审计；幂等）。
- Asset：文件与结果（对象存储索引；hash；保留策略）。
- Connector：外部资源对接（模型提供方/外部服务/渠道/用户端 agent 通道）。

## 4. 架构概览（Architecture）
前后端分离：

### 4.1 前端（Vue）
- 用户交付页：打开 token URL，展示 Skill 信息、剩余次数、上传输入、提交 Job、查看结果。
- 管理后台：Skill/SKU 管理、订单管理、Job 列表、资产查看、Webhook 配置（可逐步实现）。

### 4.2 后端（Gateway + Worker）
- Gateway（HTTP API）：
  - token 校验、计次 reserve/finalize
  - 创建 Job、查询 Job、生成 presigned URL
  - 管理 Skill/SKU/Order
  - webhook（下单成功提醒/人工协助提醒）
- Worker（异步执行）：
  - 从队列取 Job
  - 根据 Skill.type 调用对应 Runner
  - 产出 Asset，更新 Job 状态，完成扣次 finalize

### 4.3 存储与中间件（轻量优先）
- DB：开发 SQLite；生产 Postgres
- Queue：Redis + RQ（或 Celery，需统一选型）
- Object Storage：MinIO（本地/自建都可）
- Reverse Proxy：Nginx（可选）

## 5. Skill 类型与 Runner（可扩展点）
Skill.type 决定 Runner 实现：
- prompt（第一阶段主干）：对接 nanobunana（或抽象 provider）+ prompt 模板
- external_service（后续）：HTTP 调用自建/开源服务
- workflow（后续）：多步骤编排，内部调用多个子 Skill
- client_exec（后续）：生成 step plan，下发给用户端 Agent 执行（受控+审计）
- human_assist（作为 SKU 的 delivery_mode，不是 Skill.type）

Runner 统一接口（面向对象）：
- Runner.run(job) -> RunResult(assets, logs, cost, metadata)

## 6. Token 安全与计次规则（必须遵守）
- token 强随机：>= 128-bit（URL-safe）
- token.scope 限制：只允许绑定的 sku_id/skill_id 的对应能力调用
- 扣次采用两阶段：
  1) reserve：创建 Job 时预扣（冻结一次）
  2) finalize：Job 成功后确认扣除；失败则返还
- 幂等：
  - submit_job 支持 idempotency_key，避免重复扣次与重复执行
- 审计：
  - Job 全链路日志：输入 hash、输出 hash、时间戳、执行日志、退出码（如适用）
- 过期与撤销：
  - token 可过期、可撤销；撤销后不可提交新 Job，已有 Job 视策略处理

## 7. 工程结构（Repo Layout）
建议结构（可按实际调整，但需保持层次清晰）：
- backend/
  - app/
    - api/            # FastAPI 路由
    - core/           # 配置、鉴权、token service、依赖注入
    - domain/         # OOP domain models（Skill/SKU/Order/Token/Job/Asset）
    - infra/          # DB/queue/storage/connectors 实现
    - services/       # 用例层（submit job、finalize、manual delivery 等）
    - runners/        # runner 实现（prompt/external/workflow/client_exec）
  - migrations/
  - tests/
- frontend/
  - user-portal/      # Vue：token交付页
  - admin-console/    # Vue：管理后台（可后续再开）
- skills/
  - <skill_id>/
    - skill.yaml
    - prompt.md (当 type=prompt)
    - validators.py (可选)
- deploy/
  - docker-compose.yml
  - nginx.conf (可选)

## 8. 数据库表（最小必需）
必须有：
- skills, skus, orders, tokens, jobs, assets
可后续添加：
- connectors, webhooks, audit_logs, workflow_steps

## 9. API 约定（REST + 可选 WebSocket）
- /v1/public/... ：面向用户 token 使用（最小暴露）
- /v1/admin/...  ：管理端（可加 API key/JWT）
- 统一返回结构：{ code, message, data }
- Job 状态机：queued -> running -> succeeded | failed | canceled

## 10. 里程碑推进策略（Milestone Policy）
- 每个里程碑都必须可运行、可演示、可回滚。
- 先完成“图像类 prompt Skill 自动交付主干 + 人工协助 SKU 跑通”。
- 后续扩展时优先新增 Runner/Connector，不改动已稳定的 domain 与 API 语义。
- 避免过度抽象：抽象只为后续扩展服务，且必须有用例驱动。

## 11. 默认技术选型（可在 M0 最终确认）
- Backend：Python 3.11+, FastAPI, SQLAlchemy, Alembic
- Queue：Redis + RQ
- Storage：MinIO + presigned URL
- Frontend：Vue 3 + Vite + TypeScript + Pinia + Vue Router
- Deploy：docker-compose