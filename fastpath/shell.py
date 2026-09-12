"""
Project Extra — Win32 Shell Fast-Path Engine
Deterministic, zero-latency application and system utility launcher
for Windows 10/11, bypassing visual desktop searching.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Dict, List, Optional, Tuple

from extra.core.focus import (
    WindowInfo,
    find_window_by_title,
    find_windows_by_process,
    force_activate_window,
    get_foreground_window,
    list_windows,
)
from extra.core.geometry import attach_input_desktop, ensure_dpi_aware

shell32 = ctypes.windll.shell32
shell32.ShellExecuteW.argtypes = [
    wintypes.HWND,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    ctypes.c_int,
]
shell32.ShellExecuteW.restype = wintypes.HINSTANCE

SW_SHOWNORMAL = 1

# Standard Windows Built-in Tools & Common Applications
APP_REGISTRY: Dict[str, Dict[str, str]] = {
    "calc": {"target": "calc.exe", "type": "exe", "proc": "CalculatorApp.exe"},
    "calculator": {"target": "calc.exe", "type": "exe", "proc": "CalculatorApp.exe"},
    "notepad": {"target": "notepad.exe", "type": "exe", "proc": "Notepad.exe"},
    "explorer": {"target": "explorer.exe", "type": "exe", "proc": "explorer.exe"},
    "settings": {"target": "ms-settings:", "type": "uri", "proc": "SystemSettings.exe"},
    "cmd": {"target": "cmd.exe", "type": "exe", "proc": "cmd.exe"},
    "terminal": {"target": "wt.exe", "type": "exe", "proc": "WindowsTerminal.exe"},
    "powershell": {"target": "powershell.exe", "type": "exe", "proc": "powershell.exe"},
    "taskmgr": {"target": "taskmgr.exe", "type": "exe", "proc": "Taskmgr.exe"},
    "edge": {"target": "msedge.exe", "type": "browser", "proc": "msedge.exe"},
    "chrome": {"target": "chrome.exe", "type": "browser", "proc": "chrome.exe"},
    "firefox": {"target": "firefox.exe", "type": "browser", "proc": "firefox.exe"},
    "brave": {"target": "brave.exe", "type": "browser", "proc": "brave.exe"},
}

# Standard Browser Path Locations
BROWSER_CANDIDATE_PATHS = {
    "chrome.exe": [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ],
    "msedge.exe": [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
    ],
    "brave.exe": [
        os.path.expandvars(r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        os.path.expandvars(r"%LocalAppData%\BraveSoftware\Brave-Browser\Application\brave.exe"),
    ],
    "firefox.exe": [
        os.path.expandvars(r"%ProgramFiles%\Mozilla Firefox\firefox.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe"),
    ],
}


@dataclass
class LaunchResult:
    """Encapsulates the result of a deterministic application launch."""
    success: bool
    app_name: str
    target_executed: str
    hwnd: Optional[int] = None
    window_title: Optional[str] = None
    pid: Optional[int] = None
    duration_ms: float = 0.0
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "app_name": self.app_name,
            "target_executed": self.target_executed,
            "hwnd": self.hwnd,
            "window_title": self.window_title,
            "pid": self.pid,
            "duration_ms": self.duration_ms,
            "message": self.message,
        }


def resolve_executable(name: str) -> Optional[str]:
    """
    Resolves the exact absolute executable path for a given program name.
    Inspects PATH, Program Files, LocalAppData, and Windows directories.
    """
    clean_name = name.strip().lower()

    # If already an existing full path
    if os.path.isabs(name) and os.path.exists(name):
        return name

    # Check App Registry
    reg_entry = APP_REGISTRY.get(clean_name)
    target = reg_entry["target"] if reg_entry else name

    # If it's a URI protocol (e.g. ms-settings:), return directly
    if ":" in target and not target.startswith(("C:", "D:", "E:", "F:", "G:")):
        return target

    # Check candidate browser paths
    if target in BROWSER_CANDIDATE_PATHS:
        for p in BROWSER_CANDIDATE_PATHS[target]:
            if os.path.exists(p):
                return p

    # Check system PATH
    found = shutil.which(target)
    if found:
        return found

    # Fallback to appending .exe if not present
    if not target.endswith(".exe"):
        found = shutil.which(f"{target}.exe")
        if found:
            return found

    return target


def launch_app(
    app_name: str,
    args: Optional[List[str]] = None,
    wait_for_window: bool = True,
    timeout: float = 3.0,
) -> LaunchResult:
    """
    Deterministically launches an application or system tool on Windows.
    Bypasses desktop clicking and activates the resulting window.
    
    Args:
        app_name: Tool or application name (e.g. 'calc', 'notepad', 'ms-settings:', 'chrome').
        args: Optional list of command-line arguments.
        wait_for_window: If True, polls until the window is created and focused.
        timeout: Maximum seconds to wait for window appearance.
        
    Returns:
        LaunchResult with HWND, PID, and performance duration.
    """
    ensure_dpi_aware()
    attach_input_desktop()

    t_start = time.perf_counter()
    clean_app = app_name.strip().lower()
    target = resolve_executable(clean_app)

    if not target:
        return LaunchResult(
            success=False,
            app_name=app_name,
            target_executed="",
            message=f"Could not resolve application '{app_name}'.",
        )

    # Record existing windows before launch
    existing_hwnds = {w.hwnd for w in list_windows(visible_only=False)}

    # Launch via ShellExecuteW
    params = " ".join(args) if args else None
    res = shell32.ShellExecuteW(None, "open", target, params, None, SW_SHOWNORMAL)

    # ShellExecute returns > 32 on success
    if res <= 32:
        # Fallback to subprocess.Popen if ShellExecute returned error code
        try:
            cmd = [target] + (args or [])
            proc = subprocess.Popen(cmd, shell=False)
            launched_pid = proc.pid
        except Exception as e:
            return LaunchResult(
                success=False,
                app_name=app_name,
                target_executed=target,
                message=f"Failed to launch '{target}': {e}",
            )
    else:
        launched_pid = None

    matched_hwnd: Optional[int] = None
    matched_title: Optional[str] = None
    matched_pid: Optional[int] = launched_pid

    if wait_for_window:
        deadline = time.perf_counter() + timeout
        expected_proc = APP_REGISTRY.get(clean_app, {}).get("proc", "")

        while time.perf_counter() < deadline:
            time.sleep(0.1)
            current_windows = list_windows(visible_only=True)

            for win in current_windows:
                # Prioritize newly created window handles
                if win.hwnd not in existing_hwnds:
                    matched_hwnd = win.hwnd
                    matched_title = win.title
                    matched_pid = win.process_id
                    break
                # Or matches process name
                if expected_proc and win.process_name.lower() == expected_proc.lower():
                    matched_hwnd = win.hwnd
                    matched_title = win.title
                    matched_pid = win.process_id
                    break

            if matched_hwnd:
                # Force activate the new window
                force_activate_window(matched_hwnd)
                break

    duration_ms = (time.perf_counter() - t_start) * 1000.0

    return LaunchResult(
        success=True,
        app_name=app_name,
        target_executed=target,
        hwnd=matched_hwnd,
        window_title=matched_title,
        pid=matched_pid,
        duration_ms=round(duration_ms, 2),
        message=f"Successfully launched '{app_name}' ({target}) in {duration_ms:.1f} ms.",
    )


def open_uri(uri: str) -> bool:
    """Opens any web URL, folder path, or Windows protocol scheme."""
    ensure_dpi_aware()
    attach_input_desktop()
    res = shell32.ShellExecuteW(None, "open", uri.strip(), None, None, SW_SHOWNORMAL)
    return res > 32
