# 小神skills

> AI 能力商品化与自动交付平台

## 目录结构

```
├── AGENT.md                  # 项目约定（目标、架构、模型、安全）
├── README.md
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── api/              # 路由（health）
│   │   ├── core/             # 配置、数据库、依赖注入
│   │   ├── domain/           # 领域模型占位
│   │   ├── infra/            # 基础设施占位
│   │   ├── services/         # 用例层占位
│   │   ├── runners/          # Runner 占位
│   │   └── main.py           # FastAPI 入口
│   ├── migrations/           # Alembic 迁移（待初始化）
│   ├── tests/                # 单元测试
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── user-portal/          # Vue 3 用户交付页
├── deploy/
│   └── docker-compose.yml    # Postgres + Redis + MinIO + backend
└── skills/                   # Skill 定义目录（后续填充）
```

## 本地启动

### 1. 基础设施（Docker Compose）

```bash
cd deploy
docker compose up -d          # 启动 Postgres、Redis、MinIO
```

容器启动后：
| 服务     | 地址                    |
|----------|-------------------------|
| Postgres | localhost:15432         |
| Redis    | localhost:6379          |
| MinIO    | localhost:9000 (API)    |
| MinIO Console | localhost:9001     |

### 2. 后端（Backend）

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt

# 复制并编辑环境变量
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux

uvicorn app.main:app --reload
```

访问 http://localhost:8000/health 验证。

### 3. 前端（Frontend）

```bash
cd frontend/user-portal
npm install
npm run dev
```

访问 http://localhost:5173 查看空页面。

### 4. 通过 Compose 启动 Backend

```bash
cd deploy
docker compose up -d --build backend
```

后端会自动连接同网络内的 Postgres / Redis / MinIO。

## 运行测试

```bash
cd backend
pip install -r requirements.txt   # 含 dev 依赖
pytest
```

## 环境变量说明

| 变量名           | 默认值                                                     | 说明                    |
|------------------|------------------------------------------------------------|-------------------------|
| DATABASE_URL     | postgresql+asyncpg://postgres:postgres@localhost:15432/skill_platform | 数据库连接串            |
| REDIS_URL        | redis://localhost:6379/0                                   | Redis 连接串            |
| MINIO_ENDPOINT   | localhost:9000                                             | MinIO 地址              |
| MINIO_ACCESS_KEY | minioadmin                                                 | MinIO Access Key        |
| MINIO_SECRET_KEY | minioadmin                                                 | MinIO Secret Key        |
| MINIO_BUCKET     | skill-assets                                               | MinIO 存储桶名          |
| MINIO_SECURE     | false                                                      | 是否使用 HTTPS          |
| DEBUG            | false                                                      | 调试模式                |

## 后续里程碑

参见 [AGENT.md](AGENT.md) 第 10 节"里程碑推进策略"。
