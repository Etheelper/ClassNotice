@echo off
chcp 65001 >nul
echo ========================================
echo   ClassNotice 学生端启动脚本 v1.2
echo ========================================
echo.

cd /d "%~dp0"

if not exist "%APPDATA%\ClassNotice" mkdir "%APPDATA%\ClassNotice"

echo 正在启动ClassNotice学生端...
python start.py

if errorlevel 1 (
    echo.
    echo [提示] 如遇错误，请确保已安装依赖：
    echo   pip install -r requirements.txt
    pause
)
