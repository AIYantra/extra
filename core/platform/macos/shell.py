"""
Project Extra — macOS Application Launcher & Shell Fast-Path Engine
Deterministic, zero-latency application launcher routing standard app aliases
and system utilities to macOS bundles, bypassing visual searching.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple

from extra.core.platform.base import AbstractShellLauncher, LaunchResult
from extra.core.platform.macos.focus import (
    force_activate_window,
    list_windows,
)

BUILTIN_MAC_APP_REGISTRY: Dict[str, Dict[str, str]] = {
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

MAC_APP_REGISTRY: Dict[str, Dict[str, str]] = dict(BUILTIN_MAC_APP_REGISTRY)


def get_user_registry_path() -> Path:
    """Returns the sovereign persistent user-level registry JSON path in ~/.extra/."""
    p = Path.home() / ".extra"
    p.mkdir(parents=True, exist_ok=True)
    return p / "app_registry_macos.json"


def load_user_registry(custom_path: Optional[Path] = None) -> Dict[str, Dict[str, str]]:
    """
    Loads dynamic user-registered applications from ~/.extra/app_registry_macos.json
    and merges them into the active in-memory MAC_APP_REGISTRY.
    """
    reg_path = custom_path or get_user_registry_path()
    if not reg_path.exists():
        return {}
    try:
        with open(reg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, dict) and "target" in v:
                        clean_k = k.strip().lower()
                        MAC_APP_REGISTRY[clean_k] = {
                            "target": v.get("target", ""),
                            "bundle": v.get("bundle", ""),
                            "type": v.get("type", "app"),
                            "proc": v.get("proc", os.path.basename(v.get("target", ""))),
                        }
                return data
    except Exception:
        pass
    return {}


def register_app(
    name: str,
    target: str,
    bundle: Optional[str] = None,
    proc: Optional[str] = None,
    app_type: str = "app",
    persist: bool = True,
    custom_path: Optional[Path] = None,
) -> bool:
    """
    Registers a new application into Extra's macOS MAC_APP_REGISTRY
    and persists it to ~/.extra/app_registry_macos.json.
    """
    clean_name = name.strip().lower()
    if not clean_name or not target:
        return False

    proc_name = proc or os.path.basename(target)
    entry = {
        "target": target,
        "bundle": bundle or target,
        "type": app_type,
        "proc": proc_name,
    }
    MAC_APP_REGISTRY[clean_name] = entry

    if persist:
        try:
            reg_path = custom_path or get_user_registry_path()
            existing_data: Dict[str, Any] = {}
            if reg_path.exists():
                try:
                    with open(reg_path, "r", encoding="utf-8") as f:
                        existing_data = json.load(f)
                except Exception:
                    existing_data = {}
            existing_data[clean_name] = entry
            tmp_file = reg_path.with_suffix(".tmp")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(existing_data, f, indent=2, ensure_ascii=False)
            tmp_file.replace(reg_path)
            return True
        except Exception:
            return False
    return True


def get_registered_apps() -> Dict[str, Dict[str, str]]:
    """Returns a copy of all currently registered applications on macOS."""
    return dict(MAC_APP_REGISTRY)


# Cold-start merge of persistent user registry
try:
    load_user_registry()
except Exception:
    pass


STANDARD_APP_DIRS = [
    "/Applications",
    "/System/Applications",
    "/System/Applications/Utilities",
    os.path.expanduser("~/Applications"),
]


def resolve_executable(name: str, auto_register: bool = True) -> Optional[str]:
    """
    Resolves application bundle name, target executable, or URI scheme.
    Dynamically auto-registers newly discovered applications into ~/.extra/app_registry_macos.json.
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
        alias = Path(name).stem.lower()
        if auto_register:
            if alias not in MAC_APP_REGISTRY:
                register_app(alias, target=name, proc=os.path.basename(name))
            if clean not in MAC_APP_REGISTRY and clean != alias:
                register_app(clean, target=name, proc=os.path.basename(name))
        return name

    # Search standard macOS App directories
    candidate_app = f"{name}.app"
    for d in STANDARD_APP_DIRS:
        full_path = os.path.join(d, candidate_app)
        if os.path.exists(full_path):
            if auto_register and clean not in MAC_APP_REGISTRY:
                register_app(clean, target=name, bundle=full_path, proc=name)
            return full_path

    # Check PATH binaries
    which_bin = shutil.which(name)
    if which_bin:
        if auto_register and clean not in MAC_APP_REGISTRY:
            register_app(clean, target=which_bin, proc=os.path.basename(which_bin))
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

    def register_app(
        self,
        name: str,
        target: str,
        bundle: Optional[str] = None,
        proc: Optional[str] = None,
        app_type: str = "app",
        persist: bool = True,
    ) -> bool:
        return register_app(name=name, target=target, bundle=bundle, proc=proc, app_type=app_type, persist=persist)

    def get_registered_apps(self) -> Dict[str, Dict[str, str]]:
        return get_registered_apps()

    def load_user_registry(self, custom_path: Optional[Path] = None) -> Dict[str, Dict[str, str]]:
        return load_user_registry(custom_path=custom_path)

