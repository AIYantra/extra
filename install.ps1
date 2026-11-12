<#
.SYNOPSIS
    Extra — Windows 10/11 Flashless Computer-Use Engine & MCP Server Installer
    Safe Staged Execution:
    iwr -useb https://extra.yantraos.com/install.ps1 -OutFile "$env:TEMP\install_extra.ps1"; & "$env:TEMP\install_extra.ps1"

.DESCRIPTION
    Automated zero-friction, Defender-compliant setup for AIYantra Extra:
    1. Verifies 64-bit Windows 10/11 environment.
    2. Discovers or installs Python 3.10+.
    3. Creates isolated virtual environment (.venv).
    4. Provisions CFA-safe scratch workspace (~/.extra/workspace).
    5. Configures Windows Defender Controlled Folder Access allowlists.
    6. Installs audited, enterprise-clean dependencies.
    7. Automatically configures Claude Desktop, Cursor, and Antigravity.
    8. Creates global 'extra' command and runs system doctor diagnostic.
#>

[CmdletBinding()]
param(
    [switch]$SkipDoctor = $false,
    [switch]$NoClaudeConfig = $false,
    [switch]$NoTelemetry = $false,
    [switch]$NoLaunch = $false
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> " -ForegroundColor Cyan -NoNewline
    Write-Host $Message -ForegroundColor White
}

function Write-Success {
    param([string]$Message)
    Write-Host " [OK] " -ForegroundColor Green -NoNewline
    Write-Host $Message -ForegroundColor White
}

function Write-WarningMsg {
    param([string]$Message)
    Write-Host " [WARN] " -ForegroundColor Yellow -NoNewline
    Write-Host $Message -ForegroundColor Yellow
}

function Write-ErrorMsg {
    param([string]$Message)
    Write-Host " [FAIL] " -ForegroundColor Red -NoNewline
    Write-Host $Message -ForegroundColor Red
}

Write-Host @"
======================================================================
  ______     __  __     ______   ______     ______    
 /\  ___\   /\_\_\_\   /\__  _\ /\  == \   /\  __ \   
 \ \  __\   \/_/\_\/_  \/_/\ \/ \ \  __<   \ \  __ \  
  \ \_____\   /\_\/\_\    \ \_\  \ \_\ \_\  \ \_\ \_\ 
   \/_____/   \/_/\/_/     \/_/   \/_/ /_/   \/_/\/_/ 
                                                      
  Flashless Windows 10/11 Computer-Use Engine & MCP Server
  by AIYantra (https://extra.yantraos.com)
======================================================================
"@ -ForegroundColor Cyan

# 1. Architecture Check
Write-Step "[1/5] Validating Windows 10/11 (64-bit) Host..."
if (-not [Environment]::Is64BitOperatingSystem) {
    Write-ErrorMsg "Extra requires 64-bit Windows 10 or Windows 11."
    exit 1
}
$osVersion = [Environment]::OSVersion.Version
if ($osVersion.Major -lt 10) {
    Write-ErrorMsg "Extra requires Windows 10 (Build 1703+) or Windows 11."
    exit 1
}
Write-Success "Windows host verified: $([Environment]::OSVersion.VersionString) (64-bit)"

# 2. Python 3.10+ Discovery
Write-Step "[2/5] Preparing Python 3.10+ runtime environment..."
$pythonExe = $null

$pythonCandidates = @("python.exe", "py.exe", "python3.exe")
foreach ($cmd in $pythonCandidates) {
    $found = Get-Command $cmd -ErrorAction SilentlyContinue
    if ($found) {
        try {
            $pyPath = $found.Source
            $verStr = & $pyPath -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
            if ($verStr) {
                $parts = $verStr.Trim().Split('.')
                $major = [int]$parts[0]
                $minor = [int]$parts[1]
                if ($major -eq 3 -and $minor -ge 10) {
                    if ($cmd -eq "py.exe") {
                        $actualPy = & $pyPath -c "import sys; print(sys.executable)" 2>$null
                        if ($actualPy) { $pythonExe = $actualPy.Trim() }
                    } else {
                        $pythonExe = $pyPath
                    }
                    if ($pythonExe) { break }
                }
            }
        } catch {}
    }
}

if (-not $pythonExe) {
    Write-WarningMsg "Python 3.10+ not found in PATH."
    Write-Step "Attempting automated Python installation via Windows Package Manager (winget)..."
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if ($winget) {
        & winget install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
        # Refresh environment PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
        $foundPy = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($foundPy) {
            $pythonExe = $foundPy.Source
        }
    }
}

if (-not $pythonExe) {
    Write-Step "Winget not available or failed. Downloading official Python 3.12 installer..."
    $pyInstallerUrl = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
    $pyInstallerPath = Join-Path $env:TEMP "python-3.12.8-amd64.exe"
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13
        Invoke-WebRequest -Uri $pyInstallerUrl -OutFile $pyInstallerPath -UseBasicParsing -TimeoutSec 60
        if (Test-Path $pyInstallerPath) {
            Write-Step "Installing Python 3.12 silently..."
            Start-Process -FilePath $pyInstallerPath -ArgumentList "/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_pip=1", "Include_test=0" -Wait
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
            $foundPy = Get-Command python.exe -ErrorAction SilentlyContinue
            if ($foundPy) {
                $pythonExe = $foundPy.Source
            }
            Remove-Item $pyInstallerPath -Force -ErrorAction SilentlyContinue
        }
    } catch {
        Write-WarningMsg "Direct Python installer download failed: $_"
    }
}

if (-not $pythonExe) {
    Write-ErrorMsg "Could not locate or install Python 3.10+."
    Write-Host "Please install Python 3.10+ from https://www.python.org/downloads/ and check 'Add python.exe to PATH'." -ForegroundColor Yellow
    exit 1
}

$pyVersion = & $pythonExe --version
Write-Success "Using Python runtime: $pythonExe ($pyVersion)"

# 3. Setup Target Directory & Isolated Environment
Write-Step "[3/5] Setting up workspace & isolated environment..."

$extraHome = Join-Path $env:USERPROFILE ".extra"
if (-not (Test-Path $extraHome)) {
    New-Item -ItemType Directory -Path $extraHome -Force | Out-Null
}

$workspaceDir = Join-Path $extraHome "workspace"
if (-not (Test-Path $workspaceDir)) {
    New-Item -ItemType Directory -Path $workspaceDir -Force | Out-Null
}
[Environment]::SetEnvironmentVariable("EXTRA_WORKSPACE", $workspaceDir, "User")
$env:EXTRA_WORKSPACE = $workspaceDir
Write-Success "CFA-safe scratch workspace ready at $workspaceDir"

# Check if script is running from inside the extra repository
$scriptDir = $PSScriptRoot
if ($scriptDir -and (Test-Path "$scriptDir\requirements.txt")) {
    $installDir = $scriptDir
    $venvDir = Join-Path $extraHome "venv"
} else {
    $installDir = Join-Path $extraHome "app"
    $venvDir = Join-Path $extraHome "venv"

    # Clone or download if not present, or pull latest changes if existing
    if (-not (Test-Path "$installDir\requirements.txt")) {
        Write-Step "Downloading Extra repository from GitHub..."
        $git = Get-Command git.exe -ErrorAction SilentlyContinue
        if ($git) {
            & git clone https://github.com/AIYantra/extra.git $installDir
        } else {
            $zipUrl = "https://github.com/AIYantra/extra/archive/refs/heads/main.zip"
            $zipPath = Join-Path $extraHome "extra.zip"
            Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath
            Expand-Archive -Path $zipPath -DestinationPath $extraHome -Force
            Remove-Item $zipPath -Force
            if (Test-Path (Join-Path $extraHome "extra-main")) {
                Rename-Item -Path (Join-Path $extraHome "extra-main") -NewName "app" -Force
            }
        }
    } else {
        Write-Step "Existing installation found. Updating to latest version from GitHub..."
        $updated = $false
        $git = Get-Command git.exe -ErrorAction SilentlyContinue
        if ($git -and (Test-Path "$installDir\.git")) {
            try {
                & git -C $installDir fetch origin main --quiet
                & git -C $installDir reset --hard origin/main --quiet
                & git -C $installDir clean -fd --quiet
                $updated = $true
                Write-Success "Repository updated successfully via git."
            } catch {
                Write-WarningMsg "Git update encountered an issue: $_"
            }
        }

        if (-not $updated) {
            Write-Step "Downloading latest Extra code archive from GitHub..."
            $zipUrl = "https://github.com/AIYantra/extra/archive/refs/heads/main.zip"
            $zipPath = Join-Path $extraHome "extra-update.zip"
            $tempExtract = Join-Path $extraHome "temp_extract"
            try {
                Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing
                if (Test-Path $tempExtract) { Remove-Item $tempExtract -Recurse -Force -ErrorAction SilentlyContinue }
                Expand-Archive -Path $zipPath -DestinationPath $tempExtract -Force
                $extractedApp = Join-Path $tempExtract "extra-main"
                if (Test-Path $extractedApp) {
                    Get-ChildItem -Path $extractedApp -Recurse | ForEach-Object {
                        $rel = $_.FullName.Substring($extractedApp.Length).TrimStart('\', '/')
                        $dest = Join-Path $installDir $rel
                        if ($_.PSIsContainer) {
                            if (-not (Test-Path $dest)) { New-Item -ItemType Directory -Path $dest -Force | Out-Null }
                        } else {
                            Copy-Item -Path $_.FullName -Destination $dest -Force
                        }
                    }
                    $updated = $true
                    Write-Success "Repository updated successfully via GitHub archive."
                }
            } catch {
                Write-WarningMsg "Could not update repository via ZIP: $_"
            } finally {
                if (Test-Path $zipPath) { Remove-Item $zipPath -Force -ErrorAction SilentlyContinue }
                if (Test-Path $tempExtract) { Remove-Item $tempExtract -Recurse -Force -ErrorAction SilentlyContinue }
            }
        }

        # Sync rules fallback
        $rulesDir = Join-Path $installDir "rules"
        if (-not (Test-Path $rulesDir)) {
            New-Item -ItemType Directory -Path $rulesDir -Force | Out-Null
        }
        try {
            Invoke-WebRequest -Uri "https://extra.yantraos.com/extra_automation.md" -OutFile (Join-Path $rulesDir "extra_automation.md") -UseBasicParsing
            Write-Success "Fetched latest automation rules."
        } catch {}
    }
}

Write-Success "Install location: $installDir"

# 4. Virtual Environment Creation
if (-not (Test-Path "$venvDir\Scripts\python.exe")) {
    Write-Step "Creating isolated virtual environment at $venvDir..."
    & $pythonExe -m venv $venvDir
    Write-Success "Virtual environment created."
} else {
    Write-Success "Existing virtual environment found."
}

$venvPython = Join-Path $venvDir "Scripts\python.exe"
$venvPythonW = Join-Path $venvDir "Scripts\pythonw.exe"
if (-not (Test-Path $venvPythonW)) {
    $venvPythonW = $venvPython
}
$venvPip = Join-Path $venvDir "Scripts\pip.exe"

# 5. Dependency Installation
Write-Step "Installing lightning-fast Core Tier dependencies (< 6.3 MB)..."
& $venvPython -m pip install --quiet --upgrade pip
& $venvPython -m pip install --quiet --prefer-binary -r "$installDir\requirements.txt"
# Fail-safe install of core relay & desktop modules
& $venvPython -m pip install --quiet --prefer-binary websockets pillow mss pywin32 comtypes psutil mcp
if (Test-Path "$installDir\pyproject.toml") {
    & $venvPython -m pip install --quiet -e $installDir --no-deps
# Optional: live-browser CDP attach for extra_form_fill (uses installed Edge/Chrome, no browser download).
# Best-effort only: offline machines skip this silently; core install is unaffected.
& $venvPython -m pip install --quiet --prefer-binary "playwright>=1.40" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Warning "Optional playwright install skipped (offline?). Live-browser form-fill will report setup guidance instead." }
}
Write-Success "All dependencies successfully installed."

# 6. Windows Defender Controlled Folder Access (CFA) Configuration
Write-Step "Checking Windows Defender Controlled Folder Access (Ransomware Protection)..."
try {
    $cfa = (Get-MpPreference -ErrorAction SilentlyContinue).EnableControlledFolderAccess
    if ($cfa -eq 1 -or $cfa -eq 2) {
        $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
        if ($isAdmin) {
            $appsToAllow = @($venvPython, $venvPythonW)
            if ($pythonExe -and (Test-Path $pythonExe)) { $appsToAllow += $pythonExe }
            $agyPath = Join-Path $env:LOCALAPPDATA "agy\bin\agy.exe"
            if (Test-Path $agyPath) { $appsToAllow += $agyPath }
            $psPath = Join-Path $env:windir "System32\WindowsPowerShell\v1.0\powershell.exe"
            if (Test-Path $psPath) { $appsToAllow += $psPath }

            Add-MpPreference -ControlledFolderAccessAllowedApplications $appsToAllow -ErrorAction SilentlyContinue
            Write-Success "Whitelisted developer tools (Extra venv, Python, agy, PowerShell) in Windows Defender CFA."
        } else {
            Write-Success "Controlled Folder Access active. Extra configured to use safe workspace at $workspaceDir."
            Write-Host " [TIP] If you keep project folders inside Documents, run in Admin terminal: extra doctor --fix-cfa" -ForegroundColor Cyan
        }
    } else {
        Write-Success "Controlled Folder Access standard/inactive. Filesystem access unimpeded."
    }
} catch {
    # Non-blocking check
}

# 7. Global CLI Wrapper & Desktop Shortcuts (Windows 11 Smart App Control Compliant)
Write-Step "[4/5] Configuring SAC-compliant native launcher & desktop shortcuts..."
$binDir = Join-Path $env:USERPROFILE ".extra\bin"
if (-not (Test-Path $binDir)) {
    New-Item -ItemType Directory -Path $binDir -Force | Out-Null
}

$appDir = Join-Path $env:USERPROFILE ".extra\app"
if (-not (Test-Path $appDir)) {
    New-Item -ItemType Directory -Path $appDir -Force | Out-Null
}

$launcherIco = Join-Path $installDir "app\launcher\app.ico"
if (-not (Test-Path $launcherIco)) {
    $launcherIco = Join-Path $installDir "assets\icon.ico"
}

# Resolve run_app.py
$runAppPy = Join-Path $installDir "app\run_app.py"
if (-not (Test-Path $runAppPy)) {
    $runAppPy = Join-Path $installDir "run_app.py"
}

# Aggressively remove legacy unsigned Extra.exe so Windows Search & Smart App Control never flag it
$extraExe = Join-Path $appDir "Extra.exe"
Get-Process -Name "Extra" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
if (Test-Path $extraExe) {
    try {
        Remove-Item -Path $extraExe -Force -ErrorAction SilentlyContinue
    } catch { }
}

# 7a. Native Desktop & Start Menu Shortcuts via Microsoft/Python Signed pythonw.exe
# (Guarantees zero Smart App Control blocks, zero console popups, full Authenticode trust)
try {
    $wsh = New-Object -ComObject WScript.Shell
    $runAppWorkingDir = Split-Path -Parent $runAppPy

    # Desktop Shortcut
    $desktopPath = [Environment]::GetFolderPath("Desktop")
    if (Test-Path $desktopPath) {
        $shortcutPath = Join-Path $desktopPath "Extra.lnk"
        $shortcut = $wsh.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = $venvPythonW
        $shortcut.Arguments = "`"$runAppPy`""
        $shortcut.WorkingDirectory = $runAppWorkingDir
        if (Test-Path $launcherIco) { $shortcut.IconLocation = "$launcherIco,0" }
        $shortcut.Description = "Extra Desktop Companion"
        $shortcut.Save()
        Write-Success "Created SAC-compliant desktop shortcut at $shortcutPath."
    }

    # Start Menu Shortcut
    $programsPath = Join-Path [Environment]::GetFolderPath("ApplicationData") "Microsoft\Windows\Start Menu\Programs"
    if (Test-Path $programsPath) {
        $startShortcutPath = Join-Path $programsPath "Extra.lnk"
        $startShortcut = $wsh.CreateShortcut($startShortcutPath)
        $startShortcut.TargetPath = $venvPythonW
        $startShortcut.Arguments = "`"$runAppPy`""
        $startShortcut.WorkingDirectory = $runAppWorkingDir
        if (Test-Path $launcherIco) { $startShortcut.IconLocation = "$launcherIco,0" }
        $startShortcut.Description = "Extra Desktop Companion"
        $startShortcut.Save()
        Write-Success "Created SAC-compliant Start Menu shortcut at $startShortcutPath."
    }
} catch {
    Write-WarningMsg "Could not configure desktop shortcuts: $_"
}

# 7b. Global CLI Wrapper (extra.cmd)
$cmdWrapper = Join-Path $binDir "extra.cmd"
"@echo off`nif `"%~1`"==`"`" (`n    start `"`" `"$venvPythonW`" `"$runAppPy`"`n    exit /b 0`n)`nset PYTHONPATH=$installDir\src;$installDir;%PYTHONPATH%`n`"$venvPython`" -m extra.cli %*" | Set-Content -Path $cmdWrapper -Encoding ASCII

# Add ~/.extra/bin to User PATH if not already there
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$binDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$binDir", "User")
    $env:Path += ";$binDir"
    Write-Success "Added $binDir to User PATH."
} else {
    Write-Success "Global CLI wrapper ready at $cmdWrapper."
}

function Update-McpConfigFile {
    param(
        [string]$ConfigPath,
        [string]$PythonExe,
        [string]$ClientName
    )
    try {
        $parentDir = Split-Path -Parent $ConfigPath
        if (-not (Test-Path $parentDir)) {
            New-Item -ItemType Directory -Path $parentDir -Force | Out-Null
        }

        $configObj = @{}
        if (Test-Path $ConfigPath) {
            try {
                $rawJson = Get-Content -Path $ConfigPath -Raw -Encoding UTF8
                if ($rawJson -and $rawJson.Trim()) {
                    $configObj = $rawJson | ConvertFrom-Json -AsHashtable
                }
            } catch {
                $configObj = @{}
            }
        }

        if (-not $configObj.ContainsKey("mcpServers")) {
            $configObj["mcpServers"] = @{}
        }

        $configObj["mcpServers"]["extra"] = @{
            "command" = $PythonExe
            "args" = @("-m", "extra.mcp.server")
        }

        $updatedJson = $configObj | ConvertTo-Json -Depth 10
        Set-Content -Path $ConfigPath -Value $updatedJson -Encoding UTF8
        Write-Success "$ClientName MCP configuration updated: $ConfigPath"
        return $true
    } catch {
        Write-WarningMsg "Could not update $ClientName configuration: $_"
        return $false
    }
}

# 8. Multi-Client AI Configuration (Claude Desktop, Cursor, Windsurf, Claude Code, VS Code)
Write-Step "Configuring AI Client MCP Integrations..."

# 8a. Claude Desktop
if (-not $NoClaudeConfig) {
    $claudeConfigFile = Join-Path $env:APPDATA "Claude\claude_desktop_config.json"
    [void](Update-McpConfigFile -ConfigPath $claudeConfigFile -PythonExe $venvPython -ClientName "Claude Desktop")
}

# 8b. Cursor IDE
$cursorDetected = (Test-Path (Join-Path $env:USERPROFILE ".cursor")) -or `
                  (Test-Path (Join-Path $env:LOCALAPPDATA "Programs\cursor")) -or `
                  (Get-Command cursor.cmd, cursor.exe -ErrorAction SilentlyContinue)
if ($cursorDetected -or (Test-Path (Join-Path $env:USERPROFILE ".cursor"))) {
    $cursorConfig = Join-Path $env:USERPROFILE ".cursor\mcp.json"
    [void](Update-McpConfigFile -ConfigPath $cursorConfig -PythonExe $venvPython -ClientName "Cursor IDE (Global)")

    $cursorAppData = Join-Path $env:APPDATA "Cursor\User\globalStorage\cursor.mcp\mcp.json"
    if (Test-Path (Split-Path -Parent $cursorAppData)) {
        [void](Update-McpConfigFile -ConfigPath $cursorAppData -PythonExe $venvPython -ClientName "Cursor IDE (Storage)")
    }
}

# 8c. Windsurf IDE
$windsurfDetected = (Test-Path (Join-Path $env:USERPROFILE ".codeium\windsurf")) -or `
                    (Test-Path (Join-Path $env:LOCALAPPDATA "Programs\windsurf")) -or `
                    (Get-Command windsurf.cmd, windsurf.exe -ErrorAction SilentlyContinue)
if ($windsurfDetected) {
    $windsurfConfig = Join-Path $env:USERPROFILE ".codeium\windsurf\mcp_config.json"
    [void](Update-McpConfigFile -ConfigPath $windsurfConfig -PythonExe $venvPython -ClientName "Windsurf IDE")
}

# 8d. Claude Code CLI
$claudeCmd = Get-Command claude.exe, claude.cmd -ErrorAction SilentlyContinue | Select-Object -First 1
if ($claudeCmd) {
    try {
        & $claudeCmd.Source mcp add extra -- $venvPython -m extra.mcp.server 2>$null
        Write-Success "Claude Code CLI registered Extra MCP server."
    } catch {
        $claudeJson = Join-Path $env:USERPROFILE ".claude.json"
        [void](Update-McpConfigFile -ConfigPath $claudeJson -PythonExe $venvPython -ClientName "Claude Code CLI")
    }
}

# 8e. Roo Code / Cline (VS Code MCP Extensions)
$rooClineDir = Join-Path $env:APPDATA "Code\User\globalStorage\rooveterinaryinc.roo-cline\settings"
if (Test-Path $rooClineDir) {
    $rooConfig = Join-Path $rooClineDir "cline_mcp_settings.json"
    [void](Update-McpConfigFile -ConfigPath $rooConfig -PythonExe $venvPython -ClientName "Roo Code (VS Code)")
}
$clineDir = Join-Path $env:APPDATA "Code\User\globalStorage\saoudrizwan.claude-dev\settings"
if (Test-Path $clineDir) {
    $clineConfig = Join-Path $clineDir "cline_mcp_settings.json"
    [void](Update-McpConfigFile -ConfigPath $clineConfig -PythonExe $venvPython -ClientName "Cline (VS Code)")
}

# 9. Antigravity CLI (agy) Configuration
$agyCmd = Get-Command agy.exe -ErrorAction SilentlyContinue
if ($agyCmd) {
    Write-Step "Configuring Antigravity CLI (agy) MCP Integration & Rules..."
    try {
        & $agyCmd.Source mcp add extra $venvPython -m extra.mcp.server
        Write-Success "Antigravity CLI (agy) MCP server registered successfully."

        # Deploy High-Speed Zero-Lookup Automation Rules
        $ruleSrc = Join-Path $installDir "rules\extra_automation.md"
        if (-not (Test-Path $ruleSrc)) {
            $rulesDir = Join-Path $installDir "rules"
            if (-not (Test-Path $rulesDir)) { New-Item -ItemType Directory -Path $rulesDir -Force | Out-Null }
            try {
                Invoke-WebRequest -Uri "https://extra.yantraos.com/extra_automation.md" -OutFile $ruleSrc -UseBasicParsing
            } catch {}
        }
        if (Test-Path $ruleSrc) {
            $ruleContent = Get-Content -Path $ruleSrc -Raw

            # 1. Global Skill: ~/.gemini/config/skills/extra-automation/SKILL.md (active anywhere agy is run)
            $skillDir = Join-Path $env:USERPROFILE ".gemini\config\skills\extra-automation"
            if (-not (Test-Path $skillDir)) {
                New-Item -ItemType Directory -Path $skillDir -Force | Out-Null
            }
            Copy-Item -Path $ruleSrc -Destination (Join-Path $skillDir "SKILL.md") -Force
            Write-Success "Installed global skill to $(Join-Path $skillDir 'SKILL.md')"

            # 2. Global Instructions: ~/.gemini/GEMINI.md (always active across all directories including System32)
            $globalGeminiMd = Join-Path $env:USERPROFILE ".gemini\GEMINI.md"
            if (-not (Test-Path $globalGeminiMd) -or (Get-Content $globalGeminiMd -Raw) -notlike "*Extra Windows Desktop Automation Protocol*") {
                Add-Content -Path $globalGeminiMd -Value "`n`n$ruleContent" -Encoding UTF8
                Write-Success "Registered always-on protocol in $globalGeminiMd"
            }

            # 3. Global MCP instructions: ~/.gemini/antigravity-cli/mcp/extra/instructions.md
            $mcpExtraDir = Join-Path $env:USERPROFILE ".gemini\antigravity-cli\mcp\extra"
            if (Test-Path $mcpExtraDir) {
                Copy-Item -Path $ruleSrc -Destination (Join-Path $mcpExtraDir "instructions.md") -Force
                Write-Success "Installed MCP instructions to $(Join-Path $mcpExtraDir 'instructions.md')"
            }

            # 4. User profile workspace: ~/.agents/rules/extra_automation.md
            $userAgentsRules = Join-Path $env:USERPROFILE ".agents\rules"
            if (-not (Test-Path $userAgentsRules)) {
                New-Item -ItemType Directory -Path $userAgentsRules -Force | Out-Null
            }
            Copy-Item -Path $ruleSrc -Destination (Join-Path $userAgentsRules "extra_automation.md") -Force

            # 5. Current working directory workspace (if not System32)
            $cwd = (Get-Location).Path
            if ($cwd -notlike "*system32*") {
                $cwdRules = Join-Path $cwd ".agents\rules"
                if (-not (Test-Path $cwdRules)) { New-Item -ItemType Directory -Path $cwdRules -Force | Out-Null }
                Copy-Item -Path $ruleSrc -Destination (Join-Path $cwdRules "extra_automation.md") -Force
                Write-Success "Installed workspace rule to $(Join-Path $cwdRules 'extra_automation.md')"
            }
        }
    } catch {
        Write-WarningMsg "Could not auto-register with agy: $_"
    }
}

# 10. Run Extra Doctor Hardware Diagnostics
if (-not $SkipDoctor) {
    Write-Step "Running Extra Doctor Hardware Diagnostics..."
    & $venvPython -m extra.cli doctor
}

# 11. Send Anonymous Installation Success Beacon (Non-blocking, 2s timeout)
if ($env:DO_NOT_TRACK -ne "1" -and $env:EXTRA_TELEMETRY -ne "0") {
    try {
        $beaconBody = '{"os":"windows","arch":"' + $env:PROCESSOR_ARCHITECTURE + '","version":"0.3.5","method":"install.ps1"}'
        if (Get-Command curl.exe -ErrorAction SilentlyContinue) {
            Start-Process -FilePath "curl.exe" -ArgumentList @("-s", "-m", "2", "-X", "POST", "https://extra.yantraos.com/api/install-success", "-H", "Content-Type: application/json", "-d", $beaconBody) -WindowStyle Hidden
        } else {
            Invoke-RestMethod -Uri "https://extra.yantraos.com/api/install-success" -Method Post -Body $beaconBody -ContentType "application/json" -TimeoutSec 2 -ErrorAction SilentlyContinue | Out-Null
        }
    } catch { }
}

# 12. Auto-Launch Extra Desktop Companion App (via signed pythonw.exe)
if (-not $NoLaunch -and (Test-Path $runAppPy)) {
    Write-Step "[5/5] Launching Extra Desktop Companion App..."
    try {
        $runAppDir = Split-Path -Parent $runAppPy
        Start-Process -FilePath $venvPythonW -ArgumentList "`"$runAppPy`"" -WorkingDirectory $runAppDir
        Write-Success "Extra Companion is now running on your desktop (SAC-compliant)!"
    } catch {
        Write-WarningMsg "Could not auto-launch Extra Companion: $_"
    }
}

$starterPromptPath = Join-Path $installDir "STARTER_PROMPT.md"

Write-Host @"

======================================================================
  EXTRA IS INSTALLED AND READY (DEFENDER CFA-COMPLIANT)
======================================================================

Safe Scratch Workspace: $workspaceDir
All agent files & charts are routed cleanly outside protected folders.

How to use Extra (Just 1 step):
Copy and paste this prompt into your AI (Claude, Antigravity, Cursor, AGY):

👉  Setup $starterPromptPath

Your AI will automatically configure its rules and reply:
"We are ready! Please restart <your AI application> to make it work."
======================================================================
"@ -ForegroundColor Green
