<#
.SYNOPSIS
  Installs Extra Desktop (Extra by YantraOS) in one step.

.DESCRIPTION
  Downloads the Extra launcher + frozen app bundle from the GitHub
  release, writes Start Menu and Desktop shortcuts, and launches the app.
  No admin rights needed (per-user install).

.EXAMPLE
  # One-line web install:
  irm https://github.com/AIYantra/extra/releases/download/v0.3.5/Install-Extra.ps1 | iex

.PARAMETER InstallDir
  Folder the app is installed into. Defaults to %USERPROFILE%\.extra\app.

.PARAMETER Version
  Release tag to download. Defaults to v0.3.5.
#>
[CmdletBinding()]
param(
  [string]$InstallDir = (Join-Path $env:USERPROFILE ".extra\app"),
  [string]$Version = "v0.3.5"
)

$ErrorActionPreference = "Stop"

$Repo = "AIYantra/extra"
$BaseUrl = "https://github.com/$Repo/releases/download/$Version"
$Files = @("Extra.exe", "ExtraApp.exe")

function Write-Step([string]$Message) {
  Write-Host "  [Extra] $Message"
}

try {
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
} catch { }

Write-Host "======================================================================"
Write-Host "  EXTRA - one-command install ($Version)"
Write-Host "  Extra by YantraOS"
Write-Host "======================================================================"

if (-not (Test-Path $InstallDir)) {
  New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

foreach ($file in $Files) {
  $dest = Join-Path $InstallDir $file
  if (Test-Path $dest) {
    Write-Step "$file already present, skipping download."
    continue
  }
  $url = "$BaseUrl/$file"
  Write-Step "Downloading $file ..."
  try {
    Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing
  } catch {
    throw "Download failed for $url : $($_.Exception.Message)"
  }
  Write-Step "Saved $dest"
}

$launcher = Join-Path $InstallDir "Extra.exe"
if (-not (Test-Path $launcher)) {
  throw "Launcher not found at $launcher after download."
}

# Engine runtime: embedded Python + the Extra wheel from the same release,
# so the local engine works on machines without Python installed.
$pythonDir = Join-Path $env:USERPROFILE ".extra\python"
$pythonExe = Join-Path $pythonDir "python.exe"
function Test-EngineReady {
  if (-not (Test-Path $pythonExe)) { return $false }
  try {
    & $pythonExe -c "import extra.cli" 2>$null
    return ($LASTEXITCODE -eq 0)
  } catch {
    return $false
  }
}
if (-not (Test-EngineReady)) {
  Write-Step "Setting up the local engine runtime (one-time download) ..."
  if (-not (Test-Path $pythonDir)) {
    New-Item -ItemType Directory -Path $pythonDir -Force | Out-Null
  }
  $embedZip = Join-Path $pythonDir "python-embed.zip"
  Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.13.7/python-3.13.7-embed-amd64.zip" -OutFile $embedZip -UseBasicParsing
  Expand-Archive -Path $embedZip -DestinationPath $pythonDir -Force
  Remove-Item $embedZip -Force
  $pth = Join-Path $pythonDir "python313._pth"
  if (Test-Path $pth) {
    (Get-Content $pth) -replace "^#import site", "import site" | Set-Content $pth
  }
  $getPip = Join-Path $pythonDir "get-pip.py"
  Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $getPip -UseBasicParsing
  & $pythonExe $getPip --no-warn-script-location | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "pip bootstrap failed." }
  $wheelName = $null
  try {
    $rel = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/tags/$Version" -UseBasicParsing
    $wheelName = ($rel.assets | Where-Object { $_.name -like "*.whl" } | Select-Object -First 1).name
  } catch {
    Write-Step "Release metadata unreachable; skipping engine install."
  }
  if ($wheelName) {
    Write-Step "Installing engine package $wheelName ..."
    & $pythonExe -m pip install --no-warn-script-location "$BaseUrl/$wheelName" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Engine package install failed." }
  }
  if (-not (Test-EngineReady)) {
    throw "Engine runtime setup finished but extra.cli is still not importable."
  }
  Write-Step "Engine runtime ready."
} else {
  Write-Step "Engine runtime already present, skipping."
}

# Start Menu + Desktop shortcuts (per-user, no admin needed).
$shell = New-Object -ComObject WScript.Shell
$targets = @(
  (Join-Path ([Environment]::GetFolderPath("Programs")) "Extra.lnk"),
  (Join-Path ([Environment]::GetFolderPath("Desktop")) "Extra.lnk")
)
foreach ($link in $targets) {
  try {
    $shortcut = $shell.CreateShortcut($link)
    $shortcut.TargetPath = $launcher
    $shortcut.WorkingDirectory = $InstallDir
    $shortcut.Description = "Extra by YantraOS"
    $shortcut.Save()
    Write-Step "Shortcut written: $link"
  } catch {
    Write-Step "Skipping shortcut $link : $($_.Exception.Message)"
  }
}

Write-Step "Launching Extra ..."
Start-Process -FilePath $launcher -WorkingDirectory $InstallDir
Write-Step "Done. Look for the Extra window."
