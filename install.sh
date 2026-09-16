#!/usr/bin/env bash
# ==============================================================================
#   Extra — macOS Flashless Computer-Use Engine & MCP Server Installer
#   One-liner execution: curl -sSL https://extra.yantraos.com/install.sh | bash
#
#   Automated zero-friction setup for AIYantra Extra on macOS:
#   1. Verifies macOS 12.3+ (Monterey, Ventura, Sonoma, Sequoia) on Apple Silicon / Intel.
#   2. Discovers or installs Python 3.10+.
#   3. Creates isolated virtual environment (~/.extra/venv).
#   4. Installs audited Apple native PyObjC & MCP dependencies.
#   5. Automatically configures Claude Desktop (claude_desktop_config.json).
#   6. Automatically configures Antigravity CLI (agy) & deploys always-on AI rules.
#   7. Creates global 'extra' CLI and runs diagnostic doctor.
# ==============================================================================

set -eo pipefail

# Text Styling
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
WHITE='\033[1;37m'
BOLD='\033[1m'
NC='\033[0m' # No Color

write_step() {
    printf "\n${CYAN}==>${NC} ${WHITE}%s${NC}\n" "$1"
}

write_ok() {
    printf " ${GREEN}[OK]${NC} %s\n" "$1"
}

write_warn() {
    printf " ${YELLOW}[WARN]${NC} %s\n" "$1"
}

write_fail() {
    printf " ${RED}[FAIL]${NC} %s\n" "$1"
}

echo -e "${CYAN}"
cat << 'EOF'
======================================================================
  ______     __  __     ______   ______     ______    
 /\  ___\   /\_\_\_\   /\__  _\ /\  == \   /\  __ \   
 \ \  __\   \/_/\_\/_  \/_/\ \/ \ \  __<   \ \  __ \  
  \ \_____\   /\_\/\_\    \ \_\  \ \_\ \_\  \ \_\ \_\ 
   \/_____/   \/_/\/_/     \/_/   \/_/ /_/   \/_/\/_/ 
                                                      
  Flashless macOS Computer-Use Engine & MCP Server
  by AIYantra (https://extra.yantraos.com)
======================================================================
EOF
echo -e "${NC}"

# 1. OS & Architecture Verification
write_step "Validating macOS Host Environment..."

if [[ "$(uname -s)" != "Darwin" ]]; then
    write_fail "This installer is specifically engineered for macOS. Detected: $(uname -s)"
    echo -e "For Windows, install Extra by running: ${CYAN}irm https://extra.yantraos.com/install.ps1 | iex${NC}\n"
    exit 1
fi

ARCH=$(uname -m)
MACOS_VER=$(sw_vers -productVersion)
MAJOR_VER=$(echo "$MACOS_VER" | cut -d. -f1)
MINOR_VER=$(echo "$MACOS_VER" | cut -d. -f2)

if [[ "$MAJOR_VER" -lt 12 || ("$MAJOR_VER" -eq 12 && "$MINOR_VER" -lt 3) ]]; then
    write_fail "Extra requires macOS 12.3 (Monterey) or later for ScreenCaptureKit support. Detected: $MACOS_VER"
    exit 1
fi

write_ok "macOS host verified: $MACOS_VER ($ARCH architecture)"

# 2. Python 3.10+ Discovery
write_step "Discovering Python 3.10+ runtime..."

PYTHON_BIN=""
for cand in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$cand" &>/dev/null; then
        VER=$("$cand" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)
        MAJ=$(echo "$VER" | cut -d. -f1)
        MIN=$(echo "$VER" | cut -d. -f2)
        if [[ "$MAJ" -eq 3 && "$MIN" -ge 10 ]]; then
            PYTHON_BIN=$(command -v "$cand")
            break
        fi
    fi
done

if [[ -z "$PYTHON_BIN" ]]; then
    write_warn "Python 3.10+ not found in PATH."
    if command -v brew &>/dev/null; then
        write_step "Homebrew detected. Installing python@3.12 automatically..."
        brew install python@3.12
        PYTHON_BIN="$(brew --prefix python@3.12)/bin/python3"
    else
        write_fail "Please install Python 3.10+ using Homebrew ('brew install python') or from python.org."
        echo -e "Download official macOS package: ${CYAN}https://www.python.org/downloads/macos/${NC}\n"
        exit 1
    fi
fi

write_ok "Using Python runtime: $PYTHON_BIN ($("$PYTHON_BIN" --version))"

# 3. Setup Target Directory & Isolated Virtual Environment
EXTRA_HOME="$HOME/.extra"
VENV_DIR="$EXTRA_HOME/venv"
INSTALL_DIR="$EXTRA_HOME/app"

write_step "Configuring application repository & virtual environment..."
mkdir -p "$EXTRA_HOME"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/requirements.txt" && -f "$SCRIPT_DIR/pyproject.toml" ]]; then
    INSTALL_DIR="$SCRIPT_DIR"
    write_ok "Using local repository at $INSTALL_DIR"
    if [[ "$INSTALL_DIR" != "$EXTRA_HOME/app" ]]; then
        mkdir -p "$EXTRA_HOME"
        ln -sfn "$INSTALL_DIR" "$EXTRA_HOME/app" 2>/dev/null || {
            mkdir -p "$EXTRA_HOME/app"
            cp -f "$INSTALL_DIR/STARTER_PROMPT_MACOS.md" "$EXTRA_HOME/app/" 2>/dev/null || true
        }
    fi
else
    if [[ ! -f "$INSTALL_DIR/requirements.txt" ]]; then
        write_step "Cloning Extra repository from GitHub..."
        if command -v git &>/dev/null; then
            git clone --depth 1 https://github.com/AIYantra/extra.git "$INSTALL_DIR"
        else
            mkdir -p "$INSTALL_DIR"
            curl -sSL "https://github.com/AIYantra/extra/archive/refs/heads/main.tar.gz" | tar -xz -C "$EXTRA_HOME"
            mv "$EXTRA_HOME/extra-main/"* "$INSTALL_DIR/"
            rm -rf "$EXTRA_HOME/extra-main"
        fi
    else
        write_step "Existing installation found. Refreshing to latest code..."
        if [[ -d "$INSTALL_DIR/.git" ]] && command -v git &>/dev/null; then
            git -C "$INSTALL_DIR" pull --quiet || true
        fi
    fi
fi

if [[ -d "$VENV_DIR" && -f "$VENV_DIR/bin/python" ]]; then
    if "$VENV_DIR/bin/python" -c 'import sys; sys.exit(0)' &>/dev/null; then
        write_ok "Existing healthy virtual environment verified."
    else
        write_warn "Existing virtual environment is corrupted. Rebuilding..."
        rm -rf "$VENV_DIR"
        "$PYTHON_BIN" -m venv "$VENV_DIR"
        write_ok "Virtual environment cleanly recreated."
    fi
else
    write_step "Creating isolated virtual environment at $VENV_DIR..."
    rm -rf "$VENV_DIR"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    write_ok "Virtual environment created."
fi

# 4. Install Dependencies
write_step "Installing verified native Apple PyObjC & MCP dependencies..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip setuptools wheel
"$VENV_DIR/bin/pip" install --quiet -r "$INSTALL_DIR/requirements.txt"
if [[ -f "$INSTALL_DIR/pyproject.toml" ]]; then
    "$VENV_DIR/bin/pip" install --quiet -e "$INSTALL_DIR" --no-deps
fi
write_ok "All native dependencies successfully installed."

# 5. Global CLI Executable Setup
write_step "Configuring global 'extra' command wrapper..."
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"

cat << EOF > "$BIN_DIR/extra"
#!/usr/bin/env bash
export PYTHONPATH="$INSTALL_DIR:\$PYTHONPATH"
exec "$VENV_DIR/bin/python" -m extra.cli "\$@"
EOF
chmod +x "$BIN_DIR/extra"

# Ensure ~/.local/bin is in PATH in ~/.zshrc or ~/.bash_profile
SHELL_RC=""
if [[ "$SHELL" == *"zsh"* ]]; then
    SHELL_RC="$HOME/.zshrc"
elif [[ "$SHELL" == *"bash"* ]]; then
    SHELL_RC="$HOME/.bash_profile"
    [[ ! -f "$SHELL_RC" ]] && SHELL_RC="$HOME/.bashrc"
fi

if [[ -n "$SHELL_RC" ]]; then
    if ! grep -q '\.local/bin' "$SHELL_RC" 2>/dev/null; then
        echo -e '\n# Extra CLI Path\nexport PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
        write_ok "Added $BIN_DIR to $SHELL_RC"
    fi
fi
export PATH="$BIN_DIR:$PATH"
write_ok "Global CLI wrapper ready at $BIN_DIR/extra"

# 6. Configure Claude Desktop (macOS)
write_step "Configuring Claude Desktop MCP Integration..."
CLAUDE_DIR="$HOME/Library/Application Support/Claude"
CLAUDE_CONFIG="$CLAUDE_DIR/claude_desktop_config.json"
mkdir -p "$CLAUDE_DIR"

"$VENV_DIR/bin/python" - << EOF
import json, os

config_path = os.path.expanduser("$CLAUDE_CONFIG")
python_path = os.path.expanduser("$VENV_DIR/bin/python")

data = {"mcpServers": {}}
if os.path.exists(config_path):
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        pass

if "mcpServers" not in data:
    data["mcpServers"] = {}

data["mcpServers"]["extra"] = {
    "command": python_path,
    "args": ["-m", "extra.mcp.server"]
}

with open(config_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
EOF
write_ok "Claude Desktop configuration updated: $CLAUDE_CONFIG"

# 7. Configure Cursor IDE (if detected)
CURSOR_DIR="$HOME/Library/Application Support/Cursor/User/globalStorage/cursor.mcp"
CURSOR_DOT_DIR="$HOME/.cursor"
if [[ -d "$HOME/Library/Application Support/Cursor" || -d "/Applications/Cursor.app" || -d "$CURSOR_DOT_DIR" ]]; then
    write_step "Configuring Cursor MCP Integration..."
    "$VENV_DIR/bin/python" - << EOF
import json, os

python_path = os.path.expanduser("$VENV_DIR/bin/python")
targets = [
    os.path.expanduser("~/Library/Application Support/Cursor/User/globalStorage/cursor.mcp/mcp.json"),
    os.path.expanduser("~/.cursor/mcp.json")
]

for config_path in targets:
    try:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        data = {"mcpServers": {}}
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass
        if "mcpServers" not in data:
            data["mcpServers"] = {}
        data["mcpServers"]["extra"] = {
            "command": python_path,
            "args": ["-m", "extra.mcp.server"]
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass
EOF
    write_ok "Cursor MCP configuration updated."
fi

# 8. Configure Windsurf IDE (if detected)
WINDSURF_DIR="$HOME/.codeium/windsurf"
if [[ -d "$WINDSURF_DIR" || -d "/Applications/Windsurf.app" ]]; then
    write_step "Configuring Windsurf MCP Integration..."
    WINDSURF_CONFIG="$WINDSURF_DIR/mcp_config.json"
    "$VENV_DIR/bin/python" - << EOF
import json, os

python_path = os.path.expanduser("$VENV_DIR/bin/python")
config_path = os.path.expanduser("$WINDSURF_CONFIG")

try:
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    data = {"mcpServers": {}}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
    if "mcpServers" not in data:
        data["mcpServers"] = {}
    data["mcpServers"]["extra"] = {
        "command": python_path,
        "args": ["-m", "extra.mcp.server"]
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
except Exception:
    pass
EOF
    write_ok "Windsurf MCP configuration updated: $WINDSURF_CONFIG"
fi

# 9. Configure Antigravity CLI (agy) & Deploy AI Protocol Rules
if command -v agy &>/dev/null; then
    write_step "Configuring Antigravity CLI (agy) MCP Integration & Rules..."
    try_agy() {
        agy mcp add extra "$VENV_DIR/bin/python" -m extra.mcp.server &>/dev/null || true
    }
    try_agy
    write_ok "Antigravity CLI (agy) registered Extra MCP server."

    # Deploy macOS Always-On Protocol Rules
    RULE_SRC="$INSTALL_DIR/rules/extra_automation_macos.md"
    [[ ! -f "$RULE_SRC" ]] && RULE_SRC="$INSTALL_DIR/rules/extra_automation.md"

    if [[ -f "$RULE_SRC" ]]; then
        # 1. Global Skill: ~/.gemini/config/skills/extra-automation/SKILL.md
        SKILL_DIR="$HOME/.gemini/config/skills/extra-automation"
        mkdir -p "$SKILL_DIR"
        cp -f "$RULE_SRC" "$SKILL_DIR/SKILL.md"
        write_ok "Installed global skill to $SKILL_DIR/SKILL.md"

        # 2. Global Instructions: ~/.gemini/GEMINI.md
        GEMINI_MD="$HOME/.gemini/GEMINI.md"
        mkdir -p "$HOME/.gemini"
        if [[ ! -f "$GEMINI_MD" ]] || ! grep -q "Extra macOS Desktop Automation Protocol" "$GEMINI_MD" 2>/dev/null; then
            cat "$RULE_SRC" >> "$GEMINI_MD"
            write_ok "Registered always-on protocol in $GEMINI_MD"
        fi

        # 3. Global MCP instructions: ~/.gemini/antigravity-cli/mcp/extra/instructions.md
        MCP_EXTRA_DIR="$HOME/.gemini/antigravity-cli/mcp/extra"
        if [[ -d "$MCP_EXTRA_DIR" ]]; then
            cp -f "$RULE_SRC" "$MCP_EXTRA_DIR/instructions.md"
            write_ok "Installed MCP instructions to $MCP_EXTRA_DIR/instructions.md"
        fi

        # 4. User profile workspace rules: ~/.agents/rules/extra_automation.md
        USER_RULES="$HOME/.agents/rules"
        mkdir -p "$USER_RULES"
        cp -f "$RULE_SRC" "$USER_RULES/extra_automation.md"
        write_ok "Installed user rule to $USER_RULES/extra_automation.md"

        # 5. Current working directory workspace rules (if not / or /tmp)
        CWD="$(pwd)"
        if [[ "$CWD" != "/" && "$CWD" != "/tmp" && -d "$CWD/.agents" ]]; then
            mkdir -p "$CWD/.agents/rules"
            cp -f "$RULE_SRC" "$CWD/.agents/rules/extra_automation.md"
            write_ok "Installed workspace rule to $CWD/.agents/rules/extra_automation.md"
        fi
    fi
fi

# 10. Run Extra Doctor Diagnostic
write_step "Running Extra Doctor Hardware Diagnostics..."
"$VENV_DIR/bin/python" -m extra.cli doctor || true

# 11. Permissions Verification Guidance
cat << 'EOF'

----------------------------------------------------------------------
  IMPORTANT: macOS Security & Privacy Permissions Required
----------------------------------------------------------------------
  Extra requires two standard macOS permissions for computer use:

  1. Accessibility:
     Run: open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
     -> Enable: Terminal / iTerm2 / Claude / Cursor / Windsurf

  2. Screen Recording:
     Run: open "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"
     -> Enable: Terminal / iTerm2 / Claude / Cursor / Windsurf

  Once granted, verify anytime by running: extra doctor
----------------------------------------------------------------------
EOF

STARTER_PROMPT_PATH="$EXTRA_HOME/app/STARTER_PROMPT_MACOS.md"
if [[ ! -f "$STARTER_PROMPT_PATH" ]]; then
    STARTER_PROMPT_PATH="$INSTALL_DIR/STARTER_PROMPT_MACOS.md"
fi

echo -e "\n${BOLD}${GREEN}======================================================================${NC}"
echo -e "${BOLD}${GREEN}  EXTRA IS INSTALLED AND READY ON MACOS! 🚀${NC}"
echo -e "${BOLD}${GREEN}======================================================================${NC}\n"
echo -e "${WHITE}How to use Extra (Just 1 step):${NC}"
echo -e "${WHITE}Copy and paste this prompt into your AI (Claude, Antigravity, Cursor, Windsurf):${NC}\n"
echo -e "👉  ${BOLD}${CYAN}Setup $STARTER_PROMPT_PATH${NC}\n"
echo -e "${WHITE}Your AI will automatically configure its rules and reply:${NC}"
echo -e "${GREEN}\"We are ready! Please restart <your AI application> to make it work.\"${NC}"
echo -e "${BOLD}${GREEN}======================================================================${NC}\n"
