# Extra Station Launcher Script
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  EXTRA STATION - SOVEREIGN DESKTOP COCKPIT" -ForegroundColor White
Write-Host "  Light Theme | Nexsas UI | Win32 DXGI | C:\Users\AdLoa\.extra" -ForegroundColor DarkGray
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

$exePath = Join-Path $ScriptDir "dist-desktop\ExtraApp.exe"
if (Test-Path $exePath) {
    Write-Host "[OK] Starting standalone native application ($exePath)..." -ForegroundColor Green
    Start-Process -FilePath $exePath
    exit 0
}

$pyScript = Join-Path $ScriptDir "run_app.py"
if (Test-Path $pyScript) {
    Write-Host "[OK] Launching Extra Station via python run_app.py..." -ForegroundColor Green
    python run_app.py
    exit 0
}

Write-Error "Could not find ExtraApp.exe or run_app.py in $ScriptDir"
