@echo off
setlocal EnableDelayedExpansion
chcp 936 >nul 2>&1

echo ============================================================
echo  小神skills -- Build Script (Windows)
echo ============================================================

echo.
echo [1/4] ���� Python ���⻷��...
if not exist "backend\.venv" (
    python -m venv backend\.venv
    if errorlevel 1 ( echo [ERROR] �������⻷��ʧ�ܣ���ȷ���Ѱ�װ Python 3.11+ & exit /b 1 )
    echo       ���⻷���Ѵ�����backend\.venv
) else (
    echo       ���⻷���Ѵ��ڣ���������
)

echo.
echo [2/4] ��װ��� Python ����...
call backend\.venv\Scripts\activate.bat
pip install --upgrade pip -q
pip install -r backend\requirements.txt -q
if errorlevel 1 ( echo [ERROR] pip install ʧ�� & exit /b 1 )
echo       ������װ���

echo.
echo [3/4] ��װǰ������...

echo       [user-portal] npm install...
pushd frontend\user-portal
call npm install --prefer-offline
if errorlevel 1 ( echo [ERROR] user-portal npm install ʧ�� & popd & exit /b 1 )
popd

echo       [admin-console] npm install...
pushd frontend\admin-console
call npm install --prefer-offline
if errorlevel 1 ( echo [ERROR] admin-console npm install ʧ�� & popd & exit /b 1 )
popd

echo.
echo [4/4] ����ǰ��...

echo       [user-portal] npm run build...
pushd frontend\user-portal
call npm run build
if errorlevel 1 ( echo [ERROR] user-portal ����ʧ�� & popd & exit /b 1 )
popd
echo       ���frontend\user-portal\dist\

echo       [admin-console] npm run build...
pushd frontend\admin-console
call npm run build
if errorlevel 1 ( echo [ERROR] admin-console ����ʧ�� & popd & exit /b 1 )
popd
echo       ���frontend\admin-console\dist\

echo.
echo ============================================================
echo  ������ɣ����� start.bat �������з���
echo ============================================================
exit /b 0
endlocal