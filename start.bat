@echo off
setlocal EnableDelayedExpansion
chcp 936 >nul

echo ============================================================
echo  ArtForge -- Start Script (Windows)
echo ============================================================

if not exist "backend\.venv\Scripts\activate.bat" (
    echo [ERROR] �Ҳ������⻷������������ build.bat
    exit /b 1
)

if not exist "backend\.env" (
    echo [WARN]  backend\.env �����ڣ��Ѵ� .env.example ����Ĭ������
    copy /Y backend\.env.example backend\.env >nul
)

echo.
echo �ڶ����������������з���...

echo [1/4] FastAPI ���          http://localhost:8000
start "ArtForge - FastAPI" cmd /k "cd /d %~dp0backend && call .venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

echo [2/4] RQ Worker x3 (并行处理 AI 任务)
start "ArtForge - RQ Worker 1" cmd /k "cd /d %~dp0backend && call .venv\Scripts\activate.bat && python worker.py"
start "ArtForge - RQ Worker 2" cmd /k "cd /d %~dp0backend && call .venv\Scripts\activate.bat && python worker.py"
start "ArtForge - RQ Worker 3" cmd /k "cd /d %~dp0backend && call .venv\Scripts\activate.bat && python worker.py"

echo [3/4] user-portal           http://localhost:5173
start "ArtForge - user-portal" cmd /k "cd /d %~dp0frontend\user-portal && npm run dev"

echo [4/4] admin-console         http://localhost:5174
start "ArtForge - admin-console" cmd /k "cd /d %~dp0frontend\admin-console && npm run dev"

echo.
echo ============================================================
echo  �����ַ��
echo    ��� API   : http://localhost:8000
echo    API �ĵ�   : http://localhost:8000/docs
echo    �û�ǰ̨   : http://localhost:5173
echo    ������̨   : http://localhost:5174
echo ============================================================
echo  �رո�����ֱ�ӹرն�Ӧ�����д��ڼ���
echo ============================================================
exit /b 0
endlocal