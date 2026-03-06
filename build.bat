@echo off
setlocal EnableDelayedExpansion
chcp 936 >nul 2>&1

echo ============================================================
echo  ArtForge -- Build Script (Windows)
echo ============================================================

echo.
echo [1/4] 创建 Python 虚拟环境...
if not exist "backend\.venv" (
    python -m venv backend\.venv
    if errorlevel 1 ( echo [ERROR] 创建虚拟环境失败，请确认已安装 Python 3.11+ & exit /b 1 )
    echo       虚拟环境已创建：backend\.venv
) else (
    echo       虚拟环境已存在，跳过创建
)

echo.
echo [2/4] 安装后端 Python 依赖...
call backend\.venv\Scripts\activate.bat
pip install --upgrade pip -q
pip install -r backend\requirements.txt -q
if errorlevel 1 ( echo [ERROR] pip install 失败 & exit /b 1 )
echo       依赖安装完成

echo.
echo [3/4] 安装前端依赖...

echo       [user-portal] npm install...
pushd frontend\user-portal
call npm install --prefer-offline
if errorlevel 1 ( echo [ERROR] user-portal npm install 失败 & popd & exit /b 1 )
popd

echo       [admin-console] npm install...
pushd frontend\admin-console
call npm install --prefer-offline
if errorlevel 1 ( echo [ERROR] admin-console npm install 失败 & popd & exit /b 1 )
popd

echo.
echo [4/4] 构建前端...

echo       [user-portal] npm run build...
pushd frontend\user-portal
call npm run build
if errorlevel 1 ( echo [ERROR] user-portal 构建失败 & popd & exit /b 1 )
popd
echo       产物：frontend\user-portal\dist\

echo       [admin-console] npm run build...
pushd frontend\admin-console
call npm run build
if errorlevel 1 ( echo [ERROR] admin-console 构建失败 & popd & exit /b 1 )
popd
echo       产物：frontend\admin-console\dist\

echo.
echo ============================================================
echo  构建完成！运行 start.bat 启动所有服务。
echo ============================================================
exit /b 0
endlocal