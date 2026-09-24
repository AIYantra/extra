"""
Project Extra — Win32 Shell Fast-Path Engine
Deterministic, zero-latency application and system utility launcher
for Windows 10/11, bypassing visual desktop searching.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple

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
BUILTIN_APP_REGISTRY: Dict[str, Dict[str, str]] = {
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
    "store": {"target": "ms-windows-store:", "type": "uri", "proc": "WinStore.App.exe"},
}

APP_REGISTRY: Dict[str, Dict[str, str]] = dict(BUILTIN_APP_REGISTRY)


def get_user_registry_path() -> Path:
    """Returns the sovereign persistent user-level registry JSON path in ~/.extra/."""
    p = Path.home() / ".extra"
    p.mkdir(parents=True, exist_ok=True)
    return p / "app_registry.json"


def load_user_registry(custom_path: Optional[Path] = None) -> Dict[str, Dict[str, str]]:
    """
    Loads dynamic user-registered applications from ~/.extra/app_registry.json
    and merges them into the active in-memory APP_REGISTRY.
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
                        APP_REGISTRY[clean_k] = {
                            "target": v.get("target", ""),
                            "type": v.get("type", "exe"),
                            "proc": v.get("proc", os.path.basename(v.get("target", ""))),
                        }
                return data
    except Exception:
        pass
    return {}


def register_app(
    name: str,
    target: str,
    proc: Optional[str] = None,
    app_type: str = "exe",
    persist: bool = True,
    custom_path: Optional[Path] = None,
) -> bool:
    """
    Registers a new application into Extra's Fast-Path APP_REGISTRY
    and persists it to ~/.extra/app_registry.json.
    """
    clean_name = name.strip().lower()
    if not clean_name or not target:
        return False

    proc_name = proc or os.path.basename(target)
    entry = {
        "target": target,
        "type": app_type,
        "proc": proc_name,
    }
    APP_REGISTRY[clean_name] = entry

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
    """Returns a copy of all currently registered applications."""
    return dict(APP_REGISTRY)


def load_seed_registry() -> Dict[str, Dict[str, str]]:
    """Loads external application knowledge seeds into in-memory APP_REGISTRY."""
    try:
        paths = [
            Path.home() / ".extra" / "knowledge_seeds.json",
            Path(__file__).resolve().parent.parent.parent / "core" / "scout" / "knowledge_seeds.json",
            Path(__file__).resolve().parent.parent.parent.parent / "assets" / "scout" / "knowledge_seeds.json",
        ]
        seeds = None
        for p in paths:
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        seeds = json.load(f)
                    if seeds:
                        break
                except Exception:
                    pass
        if seeds:
            for app_name, data in seeds.items():
                clean = app_name.strip().lower()
                if clean not in APP_REGISTRY:
                    target = data.get("target", f"{clean}.exe")
                    proc = data.get("proc", os.path.basename(target))
                    app_type = data.get("type", "exe")
                    APP_REGISTRY[clean] = {
                        "target": target,
                        "type": app_type,
                        "proc": proc,
                    }
    except Exception:
        pass
    return APP_REGISTRY


# Cold-start merge of persistent user registry and declarative knowledge seeds
try:
    load_user_registry()
except Exception:
    pass

try:
    load_seed_registry()
except Exception:
    pass


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


def resolve_executable(name: str, auto_register: bool = True) -> Optional[str]:
    """
    Resolves the exact absolute executable path for a given program name.
    Inspects PATH, Program Files, LocalAppData, Microsoft Store WindowsApps, and Windows directories.
    (Fixes #4: Resolves Store apps like Blender, Windows Terminal, Python, credit: @harshbuttru3)
    Dynamically auto-registers newly discovered applications into ~/.extra/app_registry.json.
    """
    clean_name = name.strip().lower()

    # If already an existing full path
    if os.path.isabs(name) and os.path.exists(name):
        alias = Path(name).stem.lower()
        if auto_register:
            if alias not in APP_REGISTRY:
                register_app(alias, target=name, proc=os.path.basename(name), app_type="exe")
            if clean_name not in APP_REGISTRY and clean_name != alias:
                register_app(clean_name, target=name, proc=os.path.basename(name), app_type="exe")
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
                if auto_register and clean_name not in APP_REGISTRY:
                    register_app(clean_name, target=p, proc=os.path.basename(p), app_type="browser")
                return p

    # Check system PATH
    found = shutil.which(target)
    if found:
        if auto_register and clean_name not in APP_REGISTRY:
            register_app(clean_name, target=found, proc=os.path.basename(found), app_type="exe")
        return found

    # Fallback to appending .exe if not present
    target_exe = target if target.endswith(".exe") else f"{target}.exe"
    found = shutil.which(target_exe)
    if found:
        if auto_register and clean_name not in APP_REGISTRY:
            register_app(clean_name, target=found, proc=os.path.basename(found), app_type="exe")
        return found

    # Check %LOCALAPPDATA%\Microsoft\WindowsApps (MSIX/Store execution aliases)
    win_apps_dir = os.path.expandvars(r"%LocalAppData%\Microsoft\WindowsApps")
    store_alias = os.path.join(win_apps_dir, target_exe)
    if os.path.exists(store_alias):
        if auto_register and clean_name not in APP_REGISTRY:
            register_app(clean_name, target=store_alias, proc=os.path.basename(store_alias), app_type="exe")
        return store_alias

    # Universal Query 1: Windows App Paths Registry (HKLM & HKCU)
    try:
        import winreg
        sub_key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"
        for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(root, sub_key) as base_key:
                    try:
                        with winreg.OpenKey(base_key, target_exe) as app_key:
                            val, _ = winreg.QueryValueEx(app_key, "")
                            expanded = os.path.expandvars(val).strip('"')
                            if os.path.exists(expanded):
                                if auto_register and clean_name not in APP_REGISTRY:
                                    register_app(clean_name, target=expanded, proc=os.path.basename(expanded), app_type="exe")
                                return expanded
                    except Exception:
                        pass
            except Exception:
                pass
    except Exception:
        pass

    # Universal Query 2: Standard and vendor subdirectories via generic globs
    import glob
    base_dirs = [
        os.path.expandvars(rf"%ProgramFiles%\{target}\{target_exe}"),
        os.path.expandvars(rf"%ProgramFiles(x86)%\{target}\{target_exe}"),
        os.path.expandvars(rf"%LocalAppData%\Programs\{target}\{target_exe}"),
    ]
    for cand in base_dirs:
        if os.path.exists(cand):
            if auto_register and clean_name not in APP_REGISTRY:
                register_app(clean_name, target=cand, proc=os.path.basename(cand), app_type="exe")
            return cand

    # Universal Query 3: Generic 1-level and 2-level shallow vendor globs
    clean_target = clean_name.rstrip(".exe")
    for parent in [r"%ProgramFiles%", r"%ProgramFiles(x86)%", r"%LocalAppData%\Programs"]:
        b = os.path.expandvars(parent)
        if not os.path.isdir(b):
            continue
        # Check standard vendor directories (e.g. Program Files/*/<target_exe>)
        for m in glob.glob(os.path.join(b, "*", target_exe)):
            if os.path.isfile(m):
                if auto_register and clean_name not in APP_REGISTRY:
                    register_app(clean_name, target=m, proc=os.path.basename(m), app_type="exe")
                return m
        # Check product directories (e.g. Program Files/*<target>*/*/<target_exe>)
        for m in glob.glob(os.path.join(b, f"*{clean_target}*", "*", target_exe)):
            if os.path.isfile(m):
                if auto_register and clean_name not in APP_REGISTRY:
                    register_app(clean_name, target=m, proc=os.path.basename(m), app_type="exe")
                return m

    return target


def _format_windows_cmdline_args(args: Optional[List[str]]) -> Tuple[List[str], Optional[str]]:
    """
    Cleans, strips accidental double-quoting, and escapes arguments
    using Windows standard subprocess.list2cmdline() for ShellExecuteW.
    Guarantees arguments with spaces (like '--profile-directory=Profile 3')
    are safely quoted without splitting into invalid tokens (e.g. 0.0.0.3).
    """
    if not args:
        return [], None

    clean_args: List[str] = []
    for a in args:
        if a is None:
            continue
        s = str(a).strip()
        # Handle accidental double-quoted strings like '"--profile-directory=Profile 3"'
        if len(s) >= 2 and ((s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'"))):
            inner = s[1:-1].strip()
            if inner.count('"') % 2 == 0:
                s = inner
        clean_args.append(s)

    params = subprocess.list2cmdline(clean_args) if clean_args else None
    return clean_args, params


def launch_app(
    app_name: str,
    args: Optional[List[str]] = None,
    wait_for_window: bool = True,
    timeout: float = 3.0,
    profile: Optional[str] = None,
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
        clean_args = []
    else:
        clean_args = list(args) if args else []
        if profile:
            profile_flag = f"--profile-directory={profile}"
            if not any(a.startswith("--profile-directory") for a in clean_args):
                clean_args.append(profile_flag)

        # Universal Chromium browser crash recovery suppression
        # Detects any Chromium-based browser via process type, binary name, or directory indicators
        target_dir = os.path.dirname(target) if target else ""
        is_chromium = (
            (clean_app in APP_REGISTRY and APP_REGISTRY[clean_app].get("type") == "browser")
            or any(b in target.lower() for b in ("edge", "chrome", "brave", "opera", "vivaldi", "arc"))
            or (target_dir and os.path.exists(os.path.join(target_dir, "chrome_elf.dll")))
        )
        if is_chromium:
            suppress_flags = ["--hide-crash-restore-bubble", "--no-first-run"]
            for flag in reversed(suppress_flags):
                if flag not in clean_args:
                    clean_args.insert(0, flag)

        clean_args, params = _format_windows_cmdline_args(clean_args)

    res = shell32.ShellExecuteW(None, "open", target, params, target_dir if target_dir else None, SW_SHOWNORMAL)

    # ShellExecute returns > 32 on success
    if res <= 32:
        # Fallback to subprocess.Popen if ShellExecute returned error code
        try:
            cmd = [target] + clean_args
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
        profile: Optional[str] = None,
    ) -> LaunchResult:
        return launch_app(
            app_name=app_name,
            args=args,
            wait_for_window=wait_for_window,
            timeout=timeout,
            profile=profile,
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

    def register_app(
        self,
        name: str,
        target: str,
        proc: Optional[str] = None,
        app_type: str = "exe",
        persist: bool = True,
    ) -> bool:
        return register_app(name=name, target=target, proc=proc, app_type=app_type, persist=persist)

    def get_registered_apps(self) -> Dict[str, Dict[str, str]]:
        return get_registered_apps()

    def load_user_registry(self, custom_path: Optional[Path] = None) -> Dict[str, Dict[str, str]]:
        return load_user_registry(custom_path=custom_path)

