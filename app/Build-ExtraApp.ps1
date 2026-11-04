<#
.SYNOPSIS
  Rebuilds the frozen Extra desktop bundle (dist/ExtraApp.exe).

.DESCRIPTION
  Runs PyInstaller with the exact flags the release bundle needs:
  onefile, windowed (no console), product icon, frontend dist/ as data.
  The previous ExtraApp.exe is moved out of dist/ first so the new
  bundle never embeds the old one.
#>
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Definition)

$stage = Join-Path ([IO.Path]::GetTempPath()) "extra-build-prev"
New-Item -ItemType Directory -Path $stage -Force | Out-Null
Get-ChildItem dist/ExtraApp.exe -ErrorAction SilentlyContinue | ForEach-Object {
  Move-Item $_.FullName (Join-Path $stage "ExtraApp-prev.exe") -Force
  Write-Host "  [build] Previous bundle staged aside."
}

$python = Join-Path $env:USERPROFILE ".extra\venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
  $python = "python"
}

& $python -m PyInstaller --noconfirm --clean --onefile --windowed `
  --name ExtraApp `
  --icon src-tauri/icons/icon.ico `
  --add-data "dist;dist" `
  run_app.py

$out = Get-Item dist/ExtraApp.exe
Write-Host ("  [build] Done: {0} ({1:N1} MB)" -f $out.FullName, ($out.Length / 1MB))
