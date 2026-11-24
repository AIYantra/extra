@echo off
title Extra
cd /d "%~dp0"

echo ======================================================================
echo   EXTRA — SOVEREIGN COMPUTER-USE ENGINE
echo   Light Theme ^| Nexsas UI ^| Win32 DXGI ^| C:\Users\AdLoa\.extra
echo ======================================================================
echo.

where pythonw >nul 2>nul
if %errorlevel% equ 0 (
    start "" pythonw "%~dp0run_app.py"
    exit /b 0
)

if exist "%USERPROFILE%\.extra\venv\Scripts\pythonw.exe" (
    start "" "%USERPROFILE%\.extra\venv\Scripts\pythonw.exe" "%~dp0run_app.py"
    exit /b 0
)

where python >nul 2>nul
if %errorlevel% equ 0 (
    start "" python "%~dp0run_app.py"
    exit /b 0
)

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

echo [ERROR] Extra binary or launcher not found.
pause
