"""
Project Extra — Win32 Shell Fast-Path Engine
Deterministic, zero-latency application and system utility launcher
for Windows 10/11, bypassing visual desktop searching.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Dict, List, Optional, Tuple

from extra.core.platform.base import AbstractShellLauncher, LaunchResult
from extra.core.platform.windows.focus import (
    find_window_by_title,
    find_windows_by_process,
    force_activate_window,
    get_foreground_window,
    list_windows,
)
from extra.core.platform.windows.geometry import attach_input_desktop, ensure_dpi_aware

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
    "paint": {"target": "mspaint.exe", "type": "exe", "proc": "mspaint.exe"},
    "mspaint": {"target": "mspaint.exe", "type": "exe", "proc": "mspaint.exe"},
    "photos": {"target": "ms-photos:", "type": "uri", "proc": "Photos.exe"},
    "blender": {"target": "blender.exe", "type": "exe", "proc": "blender.exe"},
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


def resolve_executable(name: str) -> Optional[str]:
    """
    Resolves the exact absolute executable path for a given program name.
    Inspects PATH, Program Files, LocalAppData, Microsoft Store WindowsApps, and Windows directories.
    (Fixes #4: Resolves Store apps like Blender, Windows Terminal, Python, credit: @harshbuttru3)
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
    target_exe = target if target.endswith(".exe") else f"{target}.exe"
    found = shutil.which(target_exe)
    if found:
        return found

    # Check %LOCALAPPDATA%\Microsoft\WindowsApps (MSIX/Store execution aliases)
    win_apps_dir = os.path.expandvars(r"%LocalAppData%\Microsoft\WindowsApps")
    store_alias = os.path.join(win_apps_dir, target_exe)
    if os.path.exists(store_alias):
        return store_alias

    # Check common 64-bit and 32-bit Program Files directories
    program_candidates = [
        os.path.expandvars(rf"%ProgramFiles%\{target}\{target_exe}"),
        os.path.expandvars(rf"%ProgramFiles(x86)%\{target}\{target_exe}"),
        os.path.expandvars(rf"%LocalAppData%\Programs\{target}\{target_exe}"),
    ]
    for cand in program_candidates:
        if os.path.exists(cand):
            return cand

    # Specific check for Blender Foundation installations
    if clean_name == "blender" or target.lower() in ("blender", "blender.exe"):
        import glob
        blender_dirs = glob.glob(os.path.expandvars(r"%ProgramFiles%\Blender Foundation\Blender*\blender.exe"))
        if blender_dirs:
            return sorted(blender_dirs)[-1]

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
    if clean_app == "photos" and args and len(args) > 0:
        target = args[0]
        params = None
    else:
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


class WindowsShellLauncher(AbstractShellLauncher):
    """Windows implementation of the AbstractShellLauncher interface."""

    def launch_app(
        self,
        app_name: str,
        args: Optional[List[str]] = None,
        wait_for_window: bool = True,
        timeout: float = 5.0,
    ) -> LaunchResult:
        return launch_app(
            app_name=app_name,
            args=args,
            wait_for_window=wait_for_window,
            timeout=timeout,
        )

    def open_uri(self, uri: str) -> bool:
        return open_uri(uri)

    def resolve_executable(self, app_name: str) -> Optional[Tuple[str, str]]:
        target = resolve_executable(app_name)
        if not target:
            return None
        reg_entry = APP_REGISTRY.get(app_name.lower().strip())
        target_type = reg_entry["type"] if reg_entry else "exe"
        return (target, target_type)
