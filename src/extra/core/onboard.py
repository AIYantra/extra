"""
Project Extra — Universal Interactive Onboarding & Multi-Client Wiring Subsystem.
Zero-friction detection, automatic MCP client registration, and live sensory handshake.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ClientInfo:
    client_id: str
    name: str
    config_path: Optional[Path]
    is_installed: bool
    is_configured: bool
    details: str = ""


def get_default_python_executable() -> str:
    """Returns the path to the current Python or dedicated Extra virtualenv interpreter."""
    user_home = Path.home()
    if sys.platform == "win32":
        venv_python = user_home / ".extra" / "venv" / "Scripts" / "python.exe"
    else:
        venv_python = user_home / ".extra" / "venv" / "bin" / "python"

    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def _check_json_mcp_config(path: Path) -> Tuple[bool, bool]:
    """
    Checks if a JSON config exists and whether 'extra' is registered.
    Returns (exists, is_configured).
    """
    if not path.exists():
        return False, False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        servers = data.get("mcpServers", {})
        if "extra" in servers:
            return True, True
        return True, False
    except Exception:
        return True, False


def _update_json_mcp_config(path: Path, python_exe: str) -> bool:
    """Idempotently adds or updates the 'extra' MCP server entry in a JSON config."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        data: Dict[str, Any] = {}
        if path.exists():
            raw = path.read_text(encoding="utf-8").strip()
            if raw:
                try:
                    data = json.loads(raw)
                except Exception:
                    data = {}

        if "mcpServers" not in data or not isinstance(data["mcpServers"], dict):
            data["mcpServers"] = {}

        data["mcpServers"]["extra"] = {
            "command": python_exe,
            "args": ["-m", "extra.mcp.server"],
        }

        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False


def detect_installed_clients(user_home: Optional[Path] = None) -> List[ClientInfo]:
    """Scans user directories and PATH to detect all supported AI clients."""
    home = user_home or Path.home()
    clients: List[ClientInfo] = []

    # Windows AppData resolution (honor user_home mock if provided)
    if sys.platform == "win32":
        appdata_base = (home / "AppData" / "Roaming") if user_home else (Path(os.environ.get("APPDATA", "")) if os.environ.get("APPDATA") else home / "AppData" / "Roaming")
    else:
        appdata_base = home

    # 1. Cursor IDE
    cursor_global = home / ".cursor" / "mcp.json"
    if sys.platform == "win32":
        cursor_appdata = appdata_base / "Cursor" / "User" / "globalStorage" / "cursor.mcp" / "mcp.json"
    elif sys.platform == "darwin":
        cursor_appdata = home / "Library" / "Application Support" / "Cursor" / "User" / "globalStorage" / "cursor.mcp" / "mcp.json"
    else:
        cursor_appdata = home / ".config" / "Cursor" / "User" / "globalStorage" / "cursor.mcp" / "mcp.json"

    cursor_path = cursor_global if (cursor_global.exists() or not cursor_appdata.exists()) else cursor_appdata
    cursor_installed = cursor_global.exists() or cursor_appdata.exists() or (home / ".cursor").exists() or (not user_home and bool(shutil.which("cursor")))
    cursor_configured = False
    if cursor_global.exists():
        _, cursor_configured = _check_json_mcp_config(cursor_global)
    if not cursor_configured and cursor_appdata.exists():
        _, cursor_configured = _check_json_mcp_config(cursor_appdata)

    clients.append(
        ClientInfo(
            client_id="cursor",
            name="Cursor IDE",
            config_path=cursor_path,
            is_installed=cursor_installed,
            is_configured=cursor_configured,
            details=str(cursor_path),
        )
    )

    # 2. Claude Desktop
    if sys.platform == "darwin":
        claude_dir = home / "Library" / "Application Support" / "Claude"
    elif sys.platform == "win32":
        claude_dir = appdata_base / "Claude"
    else:
        claude_dir = home / ".config" / "Claude"

    claude_config = claude_dir / "claude_desktop_config.json"
    claude_installed = claude_dir.exists() or claude_config.exists()
    _, claude_configured = _check_json_mcp_config(claude_config)

    clients.append(
        ClientInfo(
            client_id="claude_desktop",
            name="Claude Desktop",
            config_path=claude_config,
            is_installed=claude_installed,
            is_configured=claude_configured,
            details=str(claude_config),
        )
    )

    # 3. Windsurf IDE
    windsurf_dir = home / ".codeium" / "windsurf"
    windsurf_config = windsurf_dir / "mcp_config.json"
    windsurf_installed = windsurf_dir.exists() or windsurf_config.exists() or bool(shutil.which("windsurf"))
    _, windsurf_configured = _check_json_mcp_config(windsurf_config)

    clients.append(
        ClientInfo(
            client_id="windsurf",
            name="Windsurf IDE",
            config_path=windsurf_config,
            is_installed=windsurf_installed,
            is_configured=windsurf_configured,
            details=str(windsurf_config),
        )
    )

    # 4. Claude Code CLI
    claude_code_config = home / ".claude.json"
    claude_cmd = shutil.which("claude")
    claude_code_installed = bool(claude_cmd) or claude_code_config.exists()
    claude_code_configured = False
    if claude_code_config.exists():
        try:
            c_data = json.loads(claude_code_config.read_text(encoding="utf-8"))
            mcp_servers = c_data.get("mcpServers", {})
            if "extra" in mcp_servers:
                claude_code_configured = True
        except Exception:
            pass

    clients.append(
        ClientInfo(
            client_id="claude_code",
            name="Claude Code CLI",
            config_path=claude_code_config,
            is_installed=claude_code_installed,
            is_configured=claude_code_configured,
            details=claude_cmd or str(claude_code_config),
        )
    )

    # 5. Antigravity CLI (agy)
    agy_cmd = shutil.which("agy")
    agy_dir = home / ".gemini" / "antigravity-cli"
    agy_installed = bool(agy_cmd) or agy_dir.exists()
    agy_configured = False
    # Check agy config if exists
    agy_config_file = home / ".gemini" / "config" / "mcp_config.json"
    if agy_config_file.exists():
        _, agy_configured = _check_json_mcp_config(agy_config_file)

    clients.append(
        ClientInfo(
            client_id="antigravity",
            name="Antigravity CLI (agy)",
            config_path=agy_config_file if agy_config_file.exists() else None,
            is_installed=agy_installed,
            is_configured=agy_configured,
            details=agy_cmd or str(agy_dir),
        )
    )

    # 6. Roo Code / Cline
    if sys.platform == "win32":
        code_storage = Path(os.environ.get("APPDATA", "")) / "Code" / "User" / "globalStorage"
    elif sys.platform == "darwin":
        code_storage = home / "Library" / "Application Support" / "Code" / "User" / "globalStorage"
    else:
        code_storage = home / ".config" / "Code" / "User" / "globalStorage"

    roo_cline_path = code_storage / "rooveterinaryinc.roo-cline" / "settings" / "cline_mcp_settings.json"
    cline_legacy_path = code_storage / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json"
    active_cline_path = roo_cline_path if roo_cline_path.parent.exists() else cline_legacy_path

    cline_installed = roo_cline_path.parent.exists() or cline_legacy_path.parent.exists()
    cline_configured = False
    if roo_cline_path.exists():
        _, cline_configured = _check_json_mcp_config(roo_cline_path)
    elif cline_legacy_path.exists():
        _, cline_configured = _check_json_mcp_config(cline_legacy_path)

    if cline_installed:
        clients.append(
            ClientInfo(
                client_id="cline",
                name="Roo Code / Cline",
                config_path=active_cline_path,
                is_installed=cline_installed,
                is_configured=cline_configured,
                details=str(active_cline_path),
            )
        )

    return clients


def configure_client(client: ClientInfo, python_exe: Optional[str] = None) -> bool:
    """Configures a single AI client to connect with Extra MCP."""
    py = python_exe or get_default_python_executable()

    if client.client_id == "claude_code":
        # First try CLI command if claude binary is available
        claude_bin = shutil.which("claude")
        if claude_bin:
            try:
                res = subprocess.run(
                    [claude_bin, "mcp", "add", "extra", "--", py, "-m", "extra.mcp.server"],
                    capture_output=True,
                    timeout=5,
                    check=False,
                )
                if res.returncode == 0:
                    return True
            except Exception:
                pass
        # Fallback to editing ~/.claude.json directly
        if client.config_path:
            return _update_json_mcp_config(client.config_path, py)
        return False

    if client.client_id == "antigravity":
        agy_bin = shutil.which("agy")
        if agy_bin:
            try:
                res = subprocess.run(
                    [agy_bin, "mcp", "add", "extra", py, "-m", "extra.mcp.server"],
                    capture_output=True,
                    timeout=5,
                    check=False,
                )
                if res.returncode == 0:
                    return True
            except Exception:
                pass
        if client.config_path:
            return _update_json_mcp_config(client.config_path, py)
        return False

    # Standard JSON-based clients (Cursor, Claude Desktop, Windsurf, Cline)
    if client.config_path:
        return _update_json_mcp_config(client.config_path, py)

    return False


def configure_all_clients(
    clients: Optional[List[ClientInfo]] = None,
    python_exe: Optional[str] = None,
) -> Dict[str, bool]:
    """Configures all detected AI clients and returns a mapping of client_id -> success."""
    active_clients = clients or detect_installed_clients()
    py = python_exe or get_default_python_executable()
    results: Dict[str, bool] = {}

    for client in active_clients:
        if client.is_installed:
            results[client.client_id] = configure_client(client, py)

    return results


def run_sensory_handshake(skip_handshake: bool = False) -> Dict[str, Any]:
    """
    Executes the 3-second live visual, acoustic, and kinetic handshake:
    1. Ambient screen edge pulse (1.2s)
    2. Smooth Bezier cursor glide (50px arc)
    3. Harmonic completion chord
    """
    if skip_handshake:
        return {"status": "skipped", "visual": False, "cursor": False, "acoustic": False}

    status: Dict[str, Any] = {"status": "ok", "visual": False, "cursor": False, "acoustic": False}

    # 1. Visual Screen Pulse & Acoustic Chime
    try:
        from extra.core.indicators import get_indicator_controller
        ctrl = get_indicator_controller()
        ctrl.task_start("Extra Sensory Handshake", monitor_index=0)
        status["visual"] = True
    except Exception:
        ctrl = None

    # 2. Smooth Kinetic Cursor Glide
    try:
        from extra.core.platform import get_cursor_position, mouse_move
        cur_x, cur_y = get_cursor_position()
        # Smooth gentle 50px arc glide and return
        steps = 12
        for i in range(1, steps + 1):
            angle = (i / float(steps)) * math.pi
            dx = int(50.0 * math.sin(angle))
            dy = int(-14.0 * math.sin(angle))
            mouse_move(cur_x + dx, cur_y + dy, notify=False)
            time.sleep(0.03)
        mouse_move(cur_x, cur_y, notify=False)
        status["cursor"] = True
    except Exception:
        pass

    # 3. Completion Chord & Dismiss
    if ctrl:
        try:
            time.sleep(0.3)
            ctrl.task_complete("Extra successfully connected to your AI assistant!", success=True)
            status["acoustic"] = True
        except Exception:
            pass

    return status
