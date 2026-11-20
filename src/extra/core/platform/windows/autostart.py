"""
Project Extra — Windows Auto-Start Registry Manager.
Configures Extra to automatically launch on Windows startup in the system tray.
Uses HKEY_CURRENT_USER to ensure zero administrative privilege elevation is required.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("extra.platform.windows.autostart")

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "Extra"


def _resolve_executable_command(minimized: bool = True) -> str:
    """
    Resolves the canonical command string to launch Extra on Windows startup.
    Prefers the compiled launcher Extra.exe; falls back to pythonw -m extra.cli serve.
    """
    user_home = Path.home()
    launcher_candidates = [
        user_home / ".extra" / "app" / "launcher" / "Extra.exe",
        user_home / ".extra" / "app" / "Extra.exe",
        Path(r"D:\yantra_workspace\extra\app\launcher\Extra.exe"),
    ]

    for cand in launcher_candidates:
        if cand.exists():
            return f'"{cand}"'

    # Fallback to pythonw.exe (windowless python interpreter)
    py_exe = sys.executable
    pyw_candidate = Path(py_exe).parent / "pythonw.exe"
    if pyw_candidate.exists():
        py_exe = str(pyw_candidate)

    cmd = f'"{py_exe}" -m extra.cli serve'
    return cmd


def is_autostart_enabled() -> bool:
    """Returns True if Extra is configured to launch on Windows startup."""
    if sys.platform != "win32":
        return False

    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
            try:
                val, _ = winreg.QueryValueEx(key, APP_NAME)
                return bool(val)
            except FileNotFoundError:
                return False
    except Exception as e:
        logger.debug("Failed to query Windows Run registry key: %s", e)
        return False


def get_autostart_info() -> Dict[str, Any]:
    """Returns diagnostic information regarding Windows startup configuration."""
    if sys.platform != "win32":
        return {
            "supported": False,
            "enabled": False,
            "platform": sys.platform,
            "message": "Auto-start is currently only supported on Windows.",
        }

    try:
        import winreg
        enabled = False
        current_cmd = ""
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
            try:
                current_cmd, _ = winreg.QueryValueEx(key, APP_NAME)
                enabled = bool(current_cmd)
            except FileNotFoundError:
                enabled = False

        return {
            "supported": True,
            "enabled": enabled,
            "current_command": current_cmd,
            "recommended_command": _resolve_executable_command(),
            "registry_key": f"HKCU\\{RUN_KEY_PATH}\\{APP_NAME}",
        }
    except Exception as e:
        return {
            "supported": True,
            "enabled": False,
            "error": str(e),
            "registry_key": f"HKCU\\{RUN_KEY_PATH}\\{APP_NAME}",
        }


def enable_autostart(minimized: bool = True) -> bool:
    """
    Registers Extra in HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run.
    Does not require Administrator rights.
    """
    if sys.platform != "win32":
        logger.warning("Auto-start registration skipped: not Windows.")
        return False

    try:
        import winreg
        cmd = _resolve_executable_command(minimized=minimized)
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        logger.info("Successfully enabled Windows auto-start: %s", cmd)
        return True
    except Exception as e:
        logger.error("Failed to enable Windows auto-start: %s", e)
        return False


def disable_autostart() -> bool:
    """
    Removes Extra from HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run.
    """
    if sys.platform != "win32":
        return False

    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            try:
                winreg.DeleteValue(key, APP_NAME)
                logger.info("Successfully disabled Windows auto-start.")
            except FileNotFoundError:
                pass
        return True
    except Exception as e:
        logger.error("Failed to disable Windows auto-start: %s", e)
        return False
