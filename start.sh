#!/usr/bin/env bash
# ============================================================
#  ArtForge — Start Script (Linux / macOS)
# ============================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# 颜色
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

VENV_DIR="backend/.venv"

# ── 检查虚拟环境 ─────────────────────────────────────────────────────
if [ ! -f "$VENV_DIR/bin/activate" ]; then
  error "找不到虚拟环境，请先运行 ./build.sh"
fi

# ── 检查 .env ────────────────────────────────────────────────────────
if [ ! -f "backend/.env" ]; then
  warn "backend/.env 不存在，已从 .env.example 复制默认配置"
  cp backend/.env.example backend/.env
fi

source "$VENV_DIR/bin/activate"

echo ""
echo "============================================================"
echo " ArtForge — Start Script (Linux / macOS)"
echo "============================================================"
echo ""

# ── 清理函数：Ctrl+C 时杀掉所有子进程 ──────────────────────────────
PIDS=()
cleanup() {
  echo ""
  echo "正在停止所有服务..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
  echo "所有服务已停止。"
  exit 0
}
trap cleanup SIGINT SIGTERM

# ── FastAPI ──────────────────────────────────────────────────────────
info "[1/4] 启动 FastAPI 后端          http://localhost:8000"
(cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload 2>&1 | sed 's/^/[fastapi]  /') &
PIDS+=($!)

sleep 1   # 等 FastAPI 先就绪

# ── RQ Worker x3 ─────────────────────────────────────────────────────
info "[2/4] 启动 RQ Worker x3 (并行处理 AI 任务)"
(cd backend && python worker.py 2>&1 | sed 's/^/[worker1] /') &
PIDS+=($!)
(cd backend && python worker.py 2>&1 | sed 's/^/[worker2] /') &
PIDS+=($!)
(cd backend && python worker.py 2>&1 | sed 's/^/[worker3] /') &
PIDS+=($!)

# ── user-portal 开发服务器 ──────────────────────────────────────────
info "[3/4] 启动 user-portal 前台      http://0.0.0.0:5173"
(cd frontend/user-portal && npm run dev -- --host 0.0.0.0 --port 5173 2>&1 | sed 's/^/[portal]  /') &
PIDS+=($!)

# ── admin-console 开发服务器 ────────────────────────────────────────
info "[4/4] 启动 admin-console 后台    http://0.0.0.0:5174"
(cd frontend/admin-console && npm run dev -- --host 0.0.0.0 --port 5174 2>&1 | sed 's/^/[admin]   /') &
PIDS+=($!)

echo ""
echo "============================================================"
echo " 所有服务已启动（输出混合显示在当前终端）："
echo "   后端 API   : http://localhost:8000"
echo "   API 文档   : http://localhost:8000/docs"
echo "   用户前台   : http://0.0.0.0:5173"
echo "   管理后台   : http://0.0.0.0:5174"
echo "============================================================"
echo " 按 Ctrl+C 停止所有服务"
echo "============================================================"
echo ""

# 等待所有子进程
wait
