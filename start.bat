@echo off
setlocal EnableDelayedExpansion

echo ============================================================
echo  xianSkill -- Start Script (Windows)
echo ============================================================

if not exist "backend\.venv\Scripts\activate.bat" (
    echo [ERROR] Virtual env not found. Please run build.bat first.
    exit /b 1
)

if not exist "backend\.env" (
    echo [WARN]  backend\.env not found. Copying from .env.example ...
    copy /Y backend\.env.example backend\.env >nul
)

echo.
echo Starting all services ...

echo [0/4] Running database migrations
call backend\.venv\Scripts\activate.bat
pushd backend
python -m alembic upgrade head
if errorlevel 1 (
    echo [ERROR] Database migration failed.
    popd
    exit /b 1
)
popd

echo [1/4] FastAPI backend      http://localhost:8000
start "xianSkill - FastAPI" cmd /k "cd /d %~dp0backend && call .venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

echo [2/4] RQ Worker x3
start "xianSkill - RQ Worker 1" cmd /k "cd /d %~dp0backend && call .venv\Scripts\activate.bat && python worker.py"
start "xianSkill - RQ Worker 2" cmd /k "cd /d %~dp0backend && call .venv\Scripts\activate.bat && python worker.py"
start "xianSkill - RQ Worker 3" cmd /k "cd /d %~dp0backend && call .venv\Scripts\activate.bat && python worker.py"

echo [3/4] user-portal          http://localhost:5173
start "xianSkill - user-portal" cmd /k "cd /d %~dp0frontend\user-portal && npm run dev"

echo [4/4] admin-console        http://localhost:5174
start "xianSkill - admin-console" cmd /k "cd /d %~dp0frontend\admin-console && npm run dev"

echo.
echo ============================================================
echo   Backend API   : http://localhost:8000
echo   API Docs      : http://localhost:8000/docs
echo   User Portal   : http://localhost:5173
echo   Admin Console : http://localhost:5174
echo ============================================================
echo   Close the opened terminal windows to stop services.
echo ============================================================
exit /b 0
endlocal
