#!/usr/bin/env bash
# ==============================================================================
#   Extra — Universal Linux & macOS Computer-Use Engine & MCP Server Installer
#   One-liner execution: curl -sSL https://extra.yantraos.com/install.sh | bash
#
#   Automated zero-friction setup for AIYantra Extra on Linux and macOS:
#   1. Detects OS: Linux (Arch, Ubuntu, Debian, Fedora, openSUSE) & macOS 12.3+.
#   2. Discovers or installs Python 3.10+.
#   3. On Linux: configures /dev/uinput permissions, udev rules & AT-SPI2 accessibility.
#   4. Creates isolated virtual environment (~/.extra/venv).
#   5. Installs audited platform-native hardware dependencies (evdev, mss, jeepney / PyObjC).
#   6. Automatically configures Claude Desktop, Antigravity (agy), Cursor & Windsurf.
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
                                                      
  Universal Autonomous Computer-Use Engine & MCP Server
  by AIYantra (https://extra.yantraos.com)
======================================================================
EOF
echo -e "${NC}"

OS_TYPE="$(uname -s)"
ARCH="$(uname -m)"

# 1. OS & Architecture Verification
write_step "Validating Host Operating System..."

if [[ "$OS_TYPE" == "Darwin" ]]; then
    MACOS_VER=$(sw_vers -productVersion)
    MAJOR_VER=$(echo "$MACOS_VER" | cut -d. -f1)
    MINOR_VER=$(echo "$MACOS_VER" | cut -d. -f2)

    if [[ "$MAJOR_VER" -lt 12 || ("$MAJOR_VER" -eq 12 && "$MINOR_VER" -lt 3) ]]; then
        write_fail "Extra requires macOS 12.3 (Monterey) or later for ScreenCaptureKit support. Detected: $MACOS_VER"
        exit 1
    fi
    write_ok "macOS host verified: $MACOS_VER ($ARCH architecture)"

elif [[ "$OS_TYPE" == "Linux" ]]; then
    DISTRO_NAME="Linux"
    if [[ -f /etc/os-release ]]; then
        DISTRO_NAME=$(grep -E '^PRETTY_NAME=' /etc/os-release | cut -d= -f2 | tr -d '"')
        [[ -z "$DISTRO_NAME" ]] && DISTRO_NAME=$(grep -E '^NAME=' /etc/os-release | cut -d= -f2 | tr -d '"')
    fi
    write_ok "Linux host verified: $DISTRO_NAME ($ARCH architecture)"

else
    write_fail "This installer supports Linux and macOS. Detected: $OS_TYPE"
    echo -e "For Windows, install Extra by running: ${CYAN}irm https://extra.yantraos.com/install.ps1 | iex${NC}\n"
    exit 1
fi

# 2. Python 3.10+ Discovery & Runtime Verification
write_step "Discovering Python 3.10+ runtime..."

PYTHON_BIN=""
for cand in python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
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
    if [[ "$OS_TYPE" == "Darwin" ]] && command -v brew &>/dev/null; then
        write_step "Homebrew detected. Installing python@3.12..."
        brew install python@3.12
        PYTHON_BIN="$(brew --prefix python@3.12)/bin/python3"
    elif [[ "$OS_TYPE" == "Linux" ]]; then
        if command -v pacman &>/dev/null; then
            write_step "Arch Linux detected. Installing python..."
            sudo pacman -S --needed --noconfirm python
            PYTHON_BIN="$(command -v python3)"
        elif command -v apt-get &>/dev/null; then
            write_step "Debian/Ubuntu detected. Installing python3-venv..."
            sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip
            PYTHON_BIN="$(command -v python3)"
        elif command -v dnf &>/dev/null; then
            write_step "Fedora detected. Installing python3..."
            sudo dnf install -y python3 python3-pip
            PYTHON_BIN="$(command -v python3)"
        fi
    fi
    if [[ -z "$PYTHON_BIN" ]]; then
        if [[ "$OS_TYPE" == "Darwin" ]]; then
            echo -e "Or download and install Python from: https://www.python.org/downloads/macos/\n"
        fi
        write_fail "Please install Python 3.10+ on your system before proceeding."
        exit 1
    fi
fi

write_ok "Using Python runtime: $PYTHON_BIN ($("$PYTHON_BIN" --version))"

# 3. Linux Hardware Permissions & Accessibility Subsystem Setup
if [[ "$OS_TYPE" == "Linux" ]]; then
    write_step "Configuring Linux hardware input and accessibility permissions..."

    # Check /dev/uinput permissions
    if [[ ! -w /dev/uinput ]]; then
        write_warn "/dev/uinput is not directly writable by current user ($USER)."
        if [[ -d /etc/udev/rules.d ]]; then
            write_step "Installing persistent /dev/uinput udev rule (group 'input')..."
            echo 'KERNEL=="uinput", MODE="0660", GROUP="input", TAG+="uaccess"' | sudo tee /etc/udev/rules.d/99-uinput.rules >/dev/null 2>&1 || true
            sudo usermod -a -G input "$USER" 2>/dev/null || true
            sudo modprobe uinput 2>/dev/null || true
            sudo udevadm control --reload-rules 2>/dev/null || true
            sudo udevadm trigger 2>/dev/null || true
            write_ok "udev rule installed. (Note: group membership takes effect upon new login or 'newgrp input')"
        fi
    else
        write_ok "/dev/uinput is write-accessible."
    fi

    # Activate AT-SPI2 accessibility if gsettings available
    if command -v gsettings &>/dev/null; then
        gsettings set org.gnome.desktop.interface toolkit-accessibility true 2>/dev/null || true
        write_ok "AT-SPI2 accessibility bus activated via gsettings."
    fi
fi

# 4. Setup Target Directory & Isolated Virtual Environment
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
        ln -sfn "$INSTALL_DIR" "$EXTRA_HOME/app" 2>/dev/null || true
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

# 5. Install Dependencies
write_step "Installing verified native dependencies & MCP engine..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip setuptools wheel

if [[ "$OS_TYPE" == "Darwin" ]]; then
    if [[ -f "$INSTALL_DIR/requirements_macos.txt" ]]; then
        "$VENV_DIR/bin/pip" install --quiet -r "$INSTALL_DIR/requirements_macos.txt"
    else
        "$VENV_DIR/bin/pip" install --quiet -r "$INSTALL_DIR/requirements.txt"
    fi
elif [[ "$OS_TYPE" == "Linux" ]]; then
    "$VENV_DIR/bin/pip" install --quiet evdev mss jeepney pillow mcp
    if [[ -f "$INSTALL_DIR/requirements.txt" ]]; then
        "$VENV_DIR/bin/pip" install --quiet -r "$INSTALL_DIR/requirements.txt" || true
    fi
fi

if [[ -f "$INSTALL_DIR/pyproject.toml" ]]; then
    "$VENV_DIR/bin/pip" install --quiet -e "$INSTALL_DIR" --no-deps
fi
write_ok "All native dependencies successfully installed."

# 6. Global CLI Executable Setup
write_step "Configuring global 'extra' command wrapper..."
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"

cat << EOF > "$BIN_DIR/extra"
#!/usr/bin/env bash
export PYTHONPATH="$INSTALL_DIR:\$PYTHONPATH"
exec "$VENV_DIR/bin/python" -m extra.cli "\$@"
EOF
chmod +x "$BIN_DIR/extra"

# Ensure ~/.local/bin is in PATH
SHELL_RC=""
if [[ "$SHELL" == *"zsh"* ]]; then
    SHELL_RC="$HOME/.zshrc"
elif [[ "$SHELL" == *"bash"* ]]; then
    SHELL_RC="$HOME/.bashrc"
    [[ ! -f "$SHELL_RC" && -f "$HOME/.bash_profile" ]] && SHELL_RC="$HOME/.bash_profile"
fi

if [[ -n "$SHELL_RC" ]]; then
    if ! grep -q '\.local/bin' "$SHELL_RC" 2>/dev/null; then
        echo -e '\n# Extra CLI Path\nexport PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
        write_ok "Added $BIN_DIR to $SHELL_RC"
    fi
fi
export PATH="$BIN_DIR:$PATH"
write_ok "Global CLI wrapper ready at $BIN_DIR/extra"

# 7. Configure Claude Desktop
write_step "Configuring Claude Desktop MCP Integration..."
if [[ "$OS_TYPE" == "Darwin" ]]; then
    CLAUDE_DIR="$HOME/Library/Application Support/Claude"
else
    CLAUDE_DIR="$HOME/.config/Claude"
fi
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

# 8. Configure Cursor IDE (if detected)
CURSOR_TARGETS=()
if [[ "$OS_TYPE" == "Darwin" ]]; then
    CURSOR_TARGETS+=(
        "$HOME/Library/Application Support/Cursor/User/globalStorage/cursor.mcp/mcp.json"
        "$HOME/.cursor/mcp.json"
    )
else
    CURSOR_TARGETS+=(
        "$HOME/.config/Cursor/User/globalStorage/cursor.mcp/mcp.json"
        "$HOME/.cursor/mcp.json"
    )
fi

"$VENV_DIR/bin/python" - << EOF
import json, os

python_path = os.path.expanduser("$VENV_DIR/bin/python")
targets = [os.path.expanduser(p) for p in "$CURSOR_TARGETS".split()]

for config_path in targets:
    try:
        if os.path.exists(os.path.dirname(config_path)):
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
write_ok "Cursor IDE integration updated."

# 9. Configure Windsurf IDE (if detected)
WINDSURF_CONFIG="$HOME/.codeium/windsurf/mcp_config.json"
if [[ -d "$HOME/.codeium/windsurf" ]]; then
    write_step "Configuring Windsurf MCP Integration..."
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

# 10. Configure Antigravity CLI (agy) & Deploy AI Protocol Rules
if command -v agy &>/dev/null; then
    write_step "Configuring Antigravity CLI (agy) MCP Integration & Rules..."
    agy mcp add extra "$VENV_DIR/bin/python" -m extra.mcp.server &>/dev/null || true
    write_ok "Antigravity CLI (agy) registered Extra MCP server."

    # Select platform-specific protocol rules
    if [[ "$OS_TYPE" == "Darwin" ]]; then
        RULE_SRC="$INSTALL_DIR/rules/extra_automation_macos.md"
    else
        RULE_SRC="$INSTALL_DIR/rules/extra_automation_linux.md"
    fi
    [[ ! -f "$RULE_SRC" ]] && RULE_SRC="$INSTALL_DIR/rules/extra_automation.md"

    if [[ -f "$RULE_SRC" ]]; then
        # 1. Global Skill: ~/.gemini/config/skills/extra-automation/SKILL.md
        SKILL_DIR="$HOME/.gemini/config/skills/extra-automation"
        mkdir -p "$SKILL_DIR"
        cp -f "$RULE_SRC" "$SKILL_DIR/SKILL.md"
        write_ok "Installed global skill to $SKILL_DIR/SKILL.md"

        # 2. Global Instructions
        GEMINI_MD="$HOME/.gemini/GEMINI.md"
        mkdir -p "$HOME/.gemini"
        if [[ ! -f "$GEMINI_MD" ]] || ! grep -q "Extra .* Desktop Automation Protocol" "$GEMINI_MD" 2>/dev/null; then
            cat "$RULE_SRC" >> "$GEMINI_MD"
            write_ok "Registered always-on protocol in $GEMINI_MD"
        fi

        # 3. Global MCP instructions: ~/.gemini/antigravity-cli/mcp/extra/instructions.md
        MCP_EXTRA_DIR="$HOME/.gemini/antigravity-cli/mcp/extra"
        mkdir -p "$MCP_EXTRA_DIR"
        cp -f "$RULE_SRC" "$MCP_EXTRA_DIR/instructions.md"
        write_ok "Installed MCP instructions to $MCP_EXTRA_DIR/instructions.md"

        # 4. User profile workspace rules
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

# 11. Run Extra Doctor Diagnostic
write_step "Running Extra Doctor Hardware Diagnostics..."
"$VENV_DIR/bin/python" -m extra.cli doctor || true

if [[ "$OS_TYPE" == "Darwin" ]]; then
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
fi

# 11b. Send Anonymous Installation Success Beacon (Non-blocking, 2s timeout)
if [[ "${DO_NOT_TRACK:-0}" != "1" && "${EXTRA_TELEMETRY:-1}" != "0" ]]; then
    (curl -s -m 2 -X POST "https://extra.yantraos.com/api/install-success" \
        -H "Content-Type: application/json" \
        -d "{\"os\":\"$OS_TYPE\",\"arch\":\"$(uname -m)\",\"version\":\"0.3.2\",\"method\":\"install.sh\"}" \
        >/dev/null 2>&1 &) || true
fi

# 12. Final Completion Banner
if [[ "$OS_TYPE" == "Darwin" ]]; then
    STARTER_PROMPT_PATH="$EXTRA_HOME/app/STARTER_PROMPT_MACOS.md"
    [[ ! -f "$STARTER_PROMPT_PATH" ]] && STARTER_PROMPT_PATH="$INSTALL_DIR/STARTER_PROMPT_MACOS.md"
    BANNER_TITLE="EXTRA IS INSTALLED AND READY ON MACOS! 🚀"
else
    STARTER_PROMPT_PATH="$EXTRA_HOME/app/STARTER_PROMPT_LINUX.md"
    [[ ! -f "$STARTER_PROMPT_PATH" ]] && STARTER_PROMPT_PATH="$INSTALL_DIR/STARTER_PROMPT_LINUX.md"
    BANNER_TITLE="EXTRA IS INSTALLED AND READY ON LINUX! 🚀"
fi

echo -e "\n${BOLD}${GREEN}======================================================================${NC}"
echo -e "${BOLD}${GREEN}  $BANNER_TITLE${NC}"
echo -e "${BOLD}${GREEN}======================================================================${NC}\n"
echo -e "${WHITE}How to use Extra (Just 1 step):${NC}"
echo -e "${WHITE}Copy and paste this prompt into your AI (Claude, Antigravity, Cursor, Windsurf):${NC}\n"
echo -e "👉  ${BOLD}${CYAN}Setup $STARTER_PROMPT_PATH${NC}\n"
echo -e "${WHITE}Your AI will automatically configure its rules and reply:${NC}"
echo -e "${GREEN}\"We are ready! Please restart <your AI application> to make it work.\"${NC}"
echo -e "${BOLD}${GREEN}======================================================================${NC}\n"
