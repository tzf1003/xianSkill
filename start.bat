@echo off
setlocal EnableDelayedExpansion
chcp 936 >nul

echo ============================================================
echo  ArtForge -- Start Script (Windows)
echo ============================================================

if not exist "backend\.venv\Scripts\activate.bat" (
    echo [ERROR] 找不到虚拟环境，请先运行 build.bat
    exit /b 1
)

if not exist "backend\.env" (
    echo [WARN]  backend\.env 不存在，已从 .env.example 复制默认配置
    copy /Y backend\.env.example backend\.env >nul
)

echo.
echo 在独立窗口中启动所有服务...

echo [1/4] FastAPI 后端          http://localhost:8000
start "ArtForge - FastAPI" cmd /k "cd /d %~dp0backend && call .venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

echo [2/4] RQ Worker
start "ArtForge - RQ Worker" cmd /k "cd /d %~dp0backend && call .venv\Scripts\activate.bat && python worker.py"

echo [3/4] user-portal           http://localhost:5173
start "ArtForge - user-portal" cmd /k "cd /d %~dp0frontend\user-portal && npm run dev"

echo [4/4] admin-console         http://localhost:5174
start "ArtForge - admin-console" cmd /k "cd /d %~dp0frontend\admin-console && npm run dev"

echo.
echo ============================================================
echo  服务地址：
echo    后端 API   : http://localhost:8000
echo    API 文档   : http://localhost:8000/docs
echo    用户前台   : http://localhost:5173
echo    管理后台   : http://localhost:5174
echo ============================================================
echo  关闭各服务：直接关闭对应命令行窗口即可
echo ============================================================
exit /b 0
endlocal