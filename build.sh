#!/usr/bin/env bash
# ============================================================
#  小神skills — Build Script (Linux / macOS)
# ============================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# 颜色
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

echo "============================================================"
echo " 小神skills — Build Script (Linux / macOS)"
echo "============================================================"

# ── 1. Python 虚拟环境 ───────────────────────────────────────────────
echo ""
info "[1/4] 创建 Python 虚拟环境..."
PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" &>/dev/null; then
  PYTHON_BIN="python"
fi
"$PYTHON_BIN" --version || error "找不到 Python，请安装 Python 3.11+"

VENV_DIR="backend/.venv"
if [ ! -d "$VENV_DIR" ]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
  info "      虚拟环境已创建：$VENV_DIR"
else
  info "      虚拟环境已存在，跳过创建"
fi

# ── 2. 安装 Python 依赖 ──────────────────────────────────────────────
echo ""
info "[2/4] 安装后端 Python 依赖..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip -q
pip install -r backend/requirements.txt -q
info "      依赖安装完成"

# ── 3. 安装前端依赖 ──────────────────────────────────────────────────
echo ""
info "[3/4] 安装前端依赖..."

info "      [user-portal] npm install..."
(cd frontend/user-portal && npm install --prefer-offline)

info "      [admin-console] npm install..."
(cd frontend/admin-console && npm install --prefer-offline)

# ── 4. 构建前端 ─────────────────────────────────────────────────────
echo ""
info "[4/4] 构建前端..."

info "      [user-portal] npm run build..."
(cd frontend/user-portal && npm run build)
info "      user-portal 产物：frontend/user-portal/dist/"

info "      [admin-console] npm run build..."
(cd frontend/admin-console && npm run build)
info "      admin-console 产物：frontend/admin-console/dist/"

echo ""
echo "============================================================"
echo " 构建完成！运行 ./start.sh 启动所有服务。"
echo "============================================================"
