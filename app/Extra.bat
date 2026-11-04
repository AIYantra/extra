@echo off
title Extra
cd /d "%~dp0"

echo ======================================================================
echo   EXTRA — SOVEREIGN COMPUTER-USE ENGINE
echo   Light Theme ^| Nexsas UI ^| Win32 DXGI ^| C:\Users\AdLoa\.extra
echo ======================================================================
echo.

if exist "dist-desktop\Extra.exe" (
    echo [OK] Starting standalone native application...
    start "" "dist-desktop\Extra.exe"
    exit /b 0
)

if exist "dist-desktop\ExtraApp.exe" (
    echo [OK] Starting standalone native application...
    start "" "dist-desktop\ExtraApp.exe"
    exit /b 0
)

if exist "run_app.py" (
    echo [OK] Launching Extra via Python environment...
    python run_app.py
    exit /b 0
)

echo [ERROR] Extra binary or launcher not found.
pause
