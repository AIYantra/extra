"""
Project Extra — macOS Application Launcher & Shell Fast-Path Engine
Deterministic, zero-latency application launcher routing standard app aliases
and system utilities to macOS bundles, bypassing visual searching.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Dict, List, Optional, Tuple

from extra.core.platform.base import AbstractShellLauncher, LaunchResult
from extra.core.platform.macos.focus import (
    force_activate_window,
    list_windows,
)

MAC_APP_REGISTRY: Dict[str, Dict[str, str]] = {
    "calc": {"target": "Calculator", "bundle": "/System/Applications/Calculator.app", "proc": "Calculator", "type": "app"},
    "calculator": {"target": "Calculator", "bundle": "/System/Applications/Calculator.app", "proc": "Calculator", "type": "app"},
    "notepad": {"target": "TextEdit", "bundle": "/System/Applications/TextEdit.app", "proc": "TextEdit", "type": "app"},
    "textedit": {"target": "TextEdit", "bundle": "/System/Applications/TextEdit.app", "proc": "TextEdit", "type": "app"},
    "explorer": {"target": "Finder", "bundle": "/System/Library/CoreServices/Finder.app", "proc": "Finder", "type": "app"},
    "finder": {"target": "Finder", "bundle": "/System/Library/CoreServices/Finder.app", "proc": "Finder", "type": "app"},
    "settings": {"target": "System Settings", "bundle": "/System/Applications/System Settings.app", "proc": "System Settings", "type": "app"},
    "terminal": {"target": "Terminal", "bundle": "/System/Applications/Utilities/Terminal.app", "proc": "Terminal", "type": "app"},
    "iterm": {"target": "iTerm2", "bundle": "/Applications/iTerm.app", "proc": "iTerm2", "type": "app"},
    "iterm2": {"target": "iTerm2", "bundle": "/Applications/iTerm.app", "proc": "iTerm2", "type": "app"},
    "safari": {"target": "Safari", "bundle": "/Applications/Safari.app", "proc": "Safari", "type": "browser"},
    "chrome": {"target": "Google Chrome", "bundle": "/Applications/Google Chrome.app", "proc": "Google Chrome", "type": "browser"},
    "edge": {"target": "Microsoft Edge", "bundle": "/Applications/Microsoft Edge.app", "proc": "Microsoft Edge", "type": "browser"},
    "brave": {"target": "Brave Browser", "bundle": "/Applications/Brave Browser.app", "proc": "Brave Browser", "type": "browser"},
    "firefox": {"target": "Firefox", "bundle": "/Applications/Firefox.app", "proc": "firefox", "type": "browser"},
    "paint": {"target": "Preview", "bundle": "/System/Applications/Preview.app", "proc": "Preview", "type": "app"},
    "preview": {"target": "Preview", "bundle": "/System/Applications/Preview.app", "proc": "Preview", "type": "app"},
    "photos": {"target": "Photos", "bundle": "/System/Applications/Photos.app", "proc": "Photos", "type": "app"},
    "code": {"target": "Visual Studio Code", "bundle": "/Applications/Visual Studio Code.app", "proc": "Code", "type": "app"},
    "vscode": {"target": "Visual Studio Code", "bundle": "/Applications/Visual Studio Code.app", "proc": "Code", "type": "app"},
}

STANDARD_APP_DIRS = [
    "/Applications",
    "/System/Applications",
    "/System/Applications/Utilities",
    os.path.expanduser("~/Applications"),
]


def resolve_executable(name: str) -> Optional[str]:
    """
    Resolves application bundle name, target executable, or URI scheme.
    """
    clean = name.strip().lower()

    # Check known registry
    if clean in MAC_APP_REGISTRY:
        return MAC_APP_REGISTRY[clean]["target"]

    # URI protocol scheme check (e.g. https://, file://, mailto:)
    if "://" in name or (":" in name and not name.startswith(("/", "."))):
        return name

    # Absolute path check
    if os.path.exists(name):
        return name

    # Search standard macOS App directories
    candidate_app = f"{name}.app"
    for d in STANDARD_APP_DIRS:
        full_path = os.path.join(d, candidate_app)
        if os.path.exists(full_path):
            return full_path

    # Check PATH binaries
    which_bin = shutil.which(name)
    if which_bin:
        return which_bin

    return name


def launch_app(
    app_name: str,
    args: Optional[List[str]] = None,
    wait_for_window: bool = True,
    timeout: float = 3.0,
) -> LaunchResult:
    """
    Launches an application or URI on macOS deterministically using `/usr/bin/open`.
    Automatically maps Windows aliases to native macOS equivalents.
    """
    t_start = time.perf_counter()
    clean = app_name.strip().lower()
    reg_entry = MAC_APP_REGISTRY.get(clean)
    target = resolve_executable(clean)

    if not target:
        return LaunchResult(
            success=False,
            app_name=app_name,
            target_executed="",
            message=f"Could not resolve application '{app_name}' on macOS.",
        )

    # Snapshot existing window IDs before launch
    existing_hwnds = set()
    try:
        existing_hwnds = {w.hwnd for w in list_windows(visible_only=False)}
    except Exception:
        pass

    # Build `open` command line
    cmd: List[str] = ["open"]
    if target.endswith(".app") or (reg_entry and reg_entry.get("type") in ("app", "browser")):
        app_spec = reg_entry["target"] if reg_entry else target
        cmd.extend(["-a", app_spec])
        
        # In macOS, files to open with an app precede --args
        file_args: List[str] = []
        flag_args: List[str] = []
        if args:
            for a in args:
                if os.path.exists(a) or not a.startswith("-"):
                    file_args.append(a)
                else:
                    flag_args.append(a)
        
        if file_args:
            cmd.extend(file_args)
        if flag_args:
            cmd.append("--args")
            cmd.extend(flag_args)
    elif "://" in target or (":" in target and not target.startswith(("/", "."))):
        # Protocol URI
        cmd.append(target)
    else:
        # Generic path or binary
        cmd.append(target)
        if args:
            cmd.extend(args)

    try:
        subprocess.Popen(cmd)
    except Exception as e:
        return LaunchResult(
            success=False,
            app_name=app_name,
            target_executed=" ".join(cmd),
            message=f"Failed to execute launch command on macOS: {e}",
        )

    matched_hwnd: Optional[int] = None
    matched_title: Optional[str] = None
    matched_pid: Optional[int] = None
    expected_proc = reg_entry.get("proc", "") if reg_entry else ""

    if wait_for_window:
        deadline = time.perf_counter() + timeout
        while time.perf_counter() < deadline:
            time.sleep(0.1)
            try:
                current_windows = list_windows(visible_only=True)
            except Exception:
                current_windows = []

            for win in current_windows:
                # Prioritize brand new window
                if win.hwnd not in existing_hwnds:
                    matched_hwnd = win.hwnd
                    matched_title = win.title
                    matched_pid = win.process_id
                    break
                # Process name match
                if expected_proc and win.process_name.lower() == expected_proc.lower():
                    matched_hwnd = win.hwnd
                    matched_title = win.title
                    matched_pid = win.process_id
                    break
                # Target title match
                if target.lower() in win.title.lower() or (reg_entry and reg_entry["target"].lower() in win.title.lower()):
                    matched_hwnd = win.hwnd
                    matched_title = win.title
                    matched_pid = win.process_id
                    break

            if matched_hwnd:
                force_activate_window(matched_hwnd)
                break

    duration_ms = (time.perf_counter() - t_start) * 1000.0

    return LaunchResult(
        success=True,
        app_name=app_name,
        target_executed=" ".join(cmd),
        hwnd=matched_hwnd,
        window_title=matched_title,
        pid=matched_pid,
        duration_ms=round(duration_ms, 2),
        message=f"Successfully launched '{app_name}' ({target}) on macOS in {duration_ms:.1f} ms.",
    )


def open_uri(uri: str) -> bool:
    """Opens any web URL, folder path, or custom protocol scheme on macOS."""
    try:
        subprocess.Popen(["open", uri.strip()])
        return True
    except Exception:
        return False


class MacShellLauncher(AbstractShellLauncher):
    """macOS implementation of the AbstractShellLauncher interface."""

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
        clean = app_name.strip().lower()
        if clean in MAC_APP_REGISTRY:
            entry = MAC_APP_REGISTRY[clean]
            return (entry["target"], entry.get("type", "app"))
        resolved = resolve_executable(app_name)
        if not resolved:
            return None
        return (resolved, "app")
