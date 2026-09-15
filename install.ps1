<#
.SYNOPSIS
    Extra — Windows 10/11 Flashless Computer-Use Engine & MCP Server Installer
    One-liner execution: irm https://extra.yantraos.com/install.ps1 | iex

.DESCRIPTION
    Automated zero-friction setup for AIYantra Extra:
    1. Verifies 64-bit Windows 10/11 environment.
    2. Discovers or installs Python 3.10+.
    3. Creates isolated virtual environment (.venv).
    4. Installs audited, enterprise-clean dependencies.
    5. Automatically configures Claude Desktop (claude_desktop_config.json).
    6. Creates global 'extra' command and runs system doctor diagnostic.
#>

[CmdletBinding()]
param(
    [switch]$SkipDoctor = $false,
    [switch]$NoClaudeConfig = $false,
    [switch]$NoTelemetry = $false
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
Write-Step "Validating Windows 10/11 (64-bit) Host..."
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
Write-Step "Checking Python runtime environment..."
$pythonExe = $null

$pythonCandidates = @("python.exe", "py.exe", "python3.exe")
foreach ($cmd in $pythonCandidates) {
    $found = Get-Command $cmd -ErrorAction SilentlyContinue
    if ($found) {
        $verStr = & $found.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($verStr) {
            $parts = $verStr.Split('.')
            $major = [int]$parts[0]
            $minor = [int]$parts[1]
            if ($major -eq 3 -and $minor -ge 10) {
                $pythonExe = $found.Source
                break
            }
        }
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
    Write-ErrorMsg "Could not locate or install Python 3.10+."
    Write-Host "Please install Python 3.10+ from https://www.python.org/downloads/ and check 'Add python.exe to PATH'." -ForegroundColor Yellow
    exit 1
}

$pyVersion = & $pythonExe --version
Write-Success "Using Python runtime: $pythonExe ($pyVersion)"

# 3. Setup Target Directory & Isolated Environment
Write-Step "Configuring application repository & virtual environment..."

# Check if script is running from inside the extra repository
$scriptDir = $PSScriptRoot
if ($scriptDir -and (Test-Path "$scriptDir\requirements.txt")) {
    $installDir = $scriptDir
    $venvDir = Join-Path $installDir ".venv"
} else {
    $extraHome = Join-Path $env:USERPROFILE ".extra"
    if (-not (Test-Path $extraHome)) {
        New-Item -ItemType Directory -Path $extraHome -Force | Out-Null
    }
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
$venvPip = Join-Path $venvDir "Scripts\pip.exe"

# 5. Dependency Installation
Write-Step "Installing verified production dependencies (Playwright, MCP, PyWin32, MSS, Comtypes)..."
& $venvPython -m pip install --quiet --upgrade pip
& $venvPython -m pip install --quiet -r "$installDir\requirements.txt"
if (Test-Path "$installDir\pyproject.toml") {
    & $venvPython -m pip install --quiet -e $installDir --no-deps
}
Write-Success "All dependencies successfully installed."

# 6. Global CLI Wrapper Setup
Write-Step "Creating global 'extra' command wrapper..."
$binDir = Join-Path $env:USERPROFILE ".extra\bin"
if (-not (Test-Path $binDir)) {
    New-Item -ItemType Directory -Path $binDir -Force | Out-Null
}

$parentDir = Split-Path -Parent $installDir
$cmdWrapper = Join-Path $binDir "extra.cmd"
"@echo off`nset PYTHONPATH=$installDir;%PYTHONPATH%`n`"$venvPython`" -m extra.cli %*" | Set-Content -Path $cmdWrapper -Encoding ASCII

# Add ~/.extra/bin to User PATH if not already there
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$binDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$binDir", "User")
    $env:Path += ";$binDir"
    Write-Success "Added $binDir to User PATH."
} else {
    Write-Success "Global CLI wrapper ready at $cmdWrapper."
}

# 7. Claude Desktop Configuration
if (-not $NoClaudeConfig) {
    Write-Step "Configuring Claude Desktop MCP Integration..."
    $claudeConfigDir = Join-Path $env:APPDATA "Claude"
    $claudeConfigFile = Join-Path $claudeConfigDir "claude_desktop_config.json"

    if (-not (Test-Path $claudeConfigDir)) {
        New-Item -ItemType Directory -Path $claudeConfigDir -Force | Out-Null
    }

    $configObj = @{}
    if (Test-Path $claudeConfigFile) {
        try {
            $rawJson = Get-Content -Path $claudeConfigFile -Raw -Encoding UTF8
            if ($rawJson.Trim()) {
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
        "command" = $venvPython
        "args" = @("-m", "extra.mcp.server")
    }

    $updatedJson = $configObj | ConvertTo-Json -Depth 10
    Set-Content -Path $claudeConfigFile -Value $updatedJson -Encoding UTF8
    Write-Success "Claude Desktop configuration updated: $claudeConfigFile"
}

# 8. Antigravity CLI (agy) Configuration
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

# 9. Run Extra Doctor Hardware Diagnostics
if (-not $SkipDoctor) {
    Write-Step "Running Extra Doctor Hardware Diagnostics..."
    & $venvPython -m extra.cli doctor
}

# 9. Anonymous Install Analytics (Non-blocking)
if (-not $env:EXTRA_NO_TELEMETRY -and -not $NoTelemetry) {
    try {
        $pyVer = "unknown"
        if ($venvPython -and (Test-Path $venvPython)) {
            $pyVer = & $venvPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>$null
        }
        $payload = @{
            event = "install_completed"
            os = [Environment]::OSVersion.VersionString
            arch = if ([Environment]::Is64BitOperatingSystem) { "x64" } else { "x86" }
            python = $pyVer
            claude_configured = (-not $NoClaudeConfig)
            timestamp = (Get-Date).ToUniversalTime().ToString("o")
        } | ConvertTo-Json -Compress

        $null = Invoke-RestMethod -Uri "https://extra.yantraos.com/api/telemetry" `
            -Method POST `
            -Body $payload `
            -ContentType "application/json" `
            -TimeoutSec 3 `
            -ErrorAction SilentlyContinue
    } catch {
        # Safe failover — telemetry failure will never interrupt installation
    }
}

$starterPromptPath = Join-Path $installDir "STARTER_PROMPT.md"

Write-Host @"

======================================================================
  EXTRA IS INSTALLED AND READY!
======================================================================

How to use Extra (Just 1 step):
Copy and paste this prompt into your AI (Claude, Antigravity, Cursor, AGY):

👉  Setup $starterPromptPath

Your AI will automatically configure its rules and reply:
"We are ready! Please restart <your AI application> to make it work."
======================================================================
"@ -ForegroundColor Green
