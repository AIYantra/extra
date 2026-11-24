# Extra Station Launcher Script
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  EXTRA STATION - SOVEREIGN DESKTOP COCKPIT" -ForegroundColor White
Write-Host "  Light Theme | Nexsas UI | Win32 DXGI | C:\Users\AdLoa\.extra" -ForegroundColor DarkGray
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

$pyScript = Join-Path $ScriptDir "run_app.py"
# Try signed pythonw first for 100% SAC compliance and zero console flash
$pyw = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
if (-not $pyw -and (Test-Path "$env:USERPROFILE\.extra\venv\Scripts\pythonw.exe")) {
    $pyw = "$env:USERPROFILE\.extra\venv\Scripts\pythonw.exe"
}

if ($pyw -and (Test-Path $pyScript)) {
    Start-Process -FilePath $pyw -ArgumentList "`"$pyScript`"" -WindowStyle Hidden
    exit 0
}

# Fallback to python.exe
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if ($py -and (Test-Path $pyScript)) {
    Start-Process -FilePath $py -ArgumentList "`"$pyScript`""
    exit 0
}

$exePath = Join-Path $ScriptDir "dist-desktop\ExtraApp.exe"
if (Test-Path $exePath) {
    Write-Host "[OK] Starting standalone native application ($exePath)..." -ForegroundColor Green
    Start-Process -FilePath $exePath
    exit 0
}

Write-Error "Could not find ExtraApp.exe or run_app.py in $ScriptDir"
