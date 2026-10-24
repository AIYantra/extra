"""
Project Extra — Linux Shell Fast-Path Engine
Deterministic application and system utility launcher via XDG Desktop Entry Specification (.desktop),
bypassing visual desktop searching on Linux.
"""

from __future__ import annotations

from dataclasses import dataclass
import glob
import json
import logging
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple

from extra.core.platform.base import AbstractShellLauncher, LaunchResult
from extra.core.platform.linux.focus import find_window_by_title, force_activate_window, get_foreground_window

logger = logging.getLogger("extra.shell.linux")

_FIELD_CODE_REGEX = re.compile(r"%[fFuUdDnNickvm%]")


def clean_exec_command(exec_str: str) -> str:
    """Strips XDG field codes (%u, %f, etc.) from an Exec line."""
    cleaned = _FIELD_CODE_REGEX.sub("", exec_str)
    return " ".join(cleaned.split())


def extract_executable(exec_clean: str) -> Optional[str]:
    """Extracts binary executable name or path from an Exec command line."""
    try:
        tokens = shlex.split(exec_clean)
    except Exception:
        tokens = exec_clean.split()
    if not tokens:
        return None

    # Handle 'env VAR=val binary ...'
    idx = 0
    if tokens[idx] == "env":
        idx += 1
        while idx < len(tokens) and ("=" in tokens[idx] or tokens[idx].startswith("-")):
            idx += 1
    if idx < len(tokens):
        bin_token = tokens[idx]
        return shutil.which(bin_token) or (bin_token if os.path.exists(bin_token) else bin_token)
    return None


@dataclass
class XDGDesktopEntry:
    """Represents a parsed freedesktop.org .desktop entry."""

    id: str
    name: str
    generic_name: str
    comment: str
    exec_raw: str
    exec_clean: str
    executable: Optional[str]
    categories: List[str]
    icon: str
    terminal: bool
    no_display: bool
    hidden: bool
    file_path: str


class XDGDesktopIndexer:
    """
    High-performance indexer for XDG Desktop entries across system, user, Flatpak, and Snap locations.
    Caches parsed entries in memory for sub-millisecond retrieval.
    """

    def __init__(self) -> None:
        self._entries: List[XDGDesktopEntry] = []
        self._by_id: Dict[str, XDGDesktopEntry] = {}
        self._by_name: Dict[str, XDGDesktopEntry] = {}
        self._by_generic_name: Dict[str, List[XDGDesktopEntry]] = {}
        self._by_bin: Dict[str, XDGDesktopEntry] = {}
        self._indexed: bool = False

    @staticmethod
    def get_search_paths() -> List[Path]:
        """Returns ordered list of directory paths where .desktop files reside."""
        paths: List[Path] = []

        # 1. User local applications
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            paths.append(Path(xdg_data_home) / "applications")
        else:
            paths.append(Path.home() / ".local" / "share" / "applications")

        # 2. XDG_DATA_DIRS system locations
        xdg_data_dirs = os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share")
        for d in xdg_data_dirs.split(":"):
            if d.strip():
                paths.append(Path(d.strip()) / "applications")

        # 3. Flatpak system and user exports
        paths.append(Path("/var/lib/flatpak/exports/share/applications"))
        paths.append(Path.home() / ".local" / "share" / "flatpak" / "exports" / "share" / "applications")

        # 4. Snap applications
        paths.append(Path("/var/lib/snapd/desktop/applications"))
        snap_gui_paths = glob.glob("/snap/*/current/meta/gui")
        for sg in snap_gui_paths:
            paths.append(Path(sg))

        # Filter to existing directories
        seen: set[str] = set()
        unique_paths: List[Path] = []
        for p in paths:
            rp = str(p.resolve()) if p.exists() else str(p)
            if p.is_dir() and rp not in seen:
                seen.add(rp)
                unique_paths.append(p)

        return unique_paths

    def index(self, force_refresh: bool = False) -> List[XDGDesktopEntry]:
        """Scans and indexes all discovered desktop files."""
        if self._indexed and not force_refresh:
            return self._entries

        self._entries.clear()
        self._by_id.clear()
        self._by_name.clear()
        self._by_generic_name.clear()
        self._by_bin.clear()

        paths = self.get_search_paths()
        for base_dir in paths:
            try:
                for entry_file in base_dir.glob("*.desktop"):
                    parsed = self._parse_file(entry_file)
                    if parsed:
                        self._entries.append(parsed)
                        # Index by id
                        clean_id = parsed.id.lower()
                        if clean_id not in self._by_id:
                            self._by_id[clean_id] = parsed
                        if clean_id.endswith(".desktop"):
                            base_id = clean_id[:-8]
                            if base_id not in self._by_id:
                                self._by_id[base_id] = parsed

                        # Index by Name
                        cname = parsed.name.strip().lower()
                        if cname and cname not in self._by_name:
                            self._by_name[cname] = parsed

                        # Index by GenericName
                        cgname = parsed.generic_name.strip().lower()
                        if cgname:
                            self._by_generic_name.setdefault(cgname, []).append(parsed)

                        # Index by Executable
                        if parsed.executable:
                            bin_name = os.path.basename(parsed.executable).lower()
                            if bin_name not in self._by_bin:
                                self._by_bin[bin_name] = parsed
            except Exception as e:
                logger.debug(f"Error scanning desktop dir {base_dir}: {e}")

        self._indexed = True
        return self._entries

    def _parse_file(self, path: Path) -> Optional[XDGDesktopEntry]:
        """Parses a single .desktop file into XDGDesktopEntry."""
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception:
            return None

        in_desktop_entry = False
        data: Dict[str, str] = {}

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                if line == "[Desktop Entry]":
                    in_desktop_entry = True
                else:
                    if in_desktop_entry:
                        # Left [Desktop Entry] section
                        break
                continue
            if in_desktop_entry and "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip()
                # Store primary keys (ignore localized variants for main keys)
                if "[" not in k and k not in data:
                    data[k] = v

        if not data:
            return None

        # Check application type
        app_type = data.get("Type", "")
        if app_type and app_type.lower() != "application":
            return None

        no_display = data.get("NoDisplay", "false").lower() == "true"
        hidden = data.get("Hidden", "false").lower() == "true"
        terminal = data.get("Terminal", "false").lower() == "true"

        exec_raw = data.get("Exec", "")
        exec_clean = clean_exec_command(exec_raw)
        executable = extract_executable(exec_clean)

        categories_str = data.get("Categories", "")
        categories = [c.strip() for c in categories_str.split(";") if c.strip()]

        return XDGDesktopEntry(
            id=path.name,
            name=data.get("Name", path.stem),
            generic_name=data.get("GenericName", ""),
            comment=data.get("Comment", ""),
            exec_raw=exec_raw,
            exec_clean=exec_clean,
            executable=executable,
            categories=categories,
            icon=data.get("Icon", ""),
            terminal=terminal,
            no_display=no_display,
            hidden=hidden,
            file_path=str(path),
        )

    def find_by_query(self, query: str) -> Optional[XDGDesktopEntry]:
        """Finds entry by query matching ID, Name, GenericName, or Executable."""
        if not self._indexed:
            self.index()

        q = query.strip().lower()

        # 1. Exact ID
        if q in self._by_id:
            return self._by_id[q]
        if f"{q}.desktop" in self._by_id:
            return self._by_id[f"{q}.desktop"]

        # 2. Exact Name
        if q in self._by_name:
            return self._by_name[q]

        # 3. Exact Executable basename
        if q in self._by_bin:
            return self._by_bin[q]

        # 4. Exact GenericName
        if q in self._by_generic_name:
            entries = self._by_generic_name[q]
            visible = [e for e in entries if not e.no_display and not e.hidden]
            return visible[0] if visible else entries[0]

        # 5. Case-insensitive substring match
        for entry in self._entries:
            if not entry.no_display and not entry.hidden:
                if q in entry.name.lower() or q in entry.generic_name.lower():
                    return entry

        return None

    def find_by_category(self, category: str) -> List[XDGDesktopEntry]:
        """Returns all entries belonging to a category (e.g. Utility, Development)."""
        if not self._indexed:
            self.index()

        cat = category.strip().lower()
        results: List[XDGDesktopEntry] = []
        for entry in self._entries:
            if not entry.no_display and not entry.hidden:
                for c in entry.categories:
                    if c.lower() == cat:
                        results.append(entry)
                        break
        return results

    def resolve_app(self, app_name: str) -> Optional[str]:
        """Returns executable path for app name or desktop entry."""
        entry = self.find_by_query(app_name)
        if entry and entry.executable:
            return entry.executable
        return None


_indexer_instance: Optional[XDGDesktopIndexer] = None


def get_desktop_indexer() -> XDGDesktopIndexer:
    """Returns singleton instance of XDGDesktopIndexer."""
    global _indexer_instance
    if _indexer_instance is None:
        _indexer_instance = XDGDesktopIndexer()
    return _indexer_instance


# ── Built-in Application Fallbacks & Semantic Registry ────────────────────────

BUILTIN_APP_FALLBACKS: Dict[str, Dict[str, Any]] = {
    # Clock & Timer
    "clock": {
        "candidates": ["gnome-clocks", "kclock", "alarm-clock-applet"],
        "type": "bin",
        "proc": "clocks",
    },
    "timer": {
        "candidates": ["gnome-clocks", "kclock", "alarm-clock-applet"],
        "type": "bin",
        "proc": "clocks",
    },

    # Calculator
    "calc": {
        "candidates": ["kcalc", "gnome-calculator", "galculator", "xcalc", "speedcrunch", "qalculate-gtk", "bc"],
        "type": "bin",
        "proc": "calc",
    },
    "calculator": {
        "candidates": ["kcalc", "gnome-calculator", "galculator", "xcalc", "speedcrunch", "qalculate-gtk", "bc"],
        "type": "bin",
        "proc": "calculator",
    },
    "kcalc": {"candidates": ["kcalc"], "type": "bin", "proc": "kcalc"},
    "gnome-calculator": {"candidates": ["gnome-calculator"], "type": "bin", "proc": "gnome-calculator"},

    # Text Editor
    "notepad": {
        "candidates": ["kate", "kwrite", "gedit", "mousepad", "xed", "pluma", "featherpad", "geany", "leafpad", "nano"],
        "type": "bin",
        "proc": "notepad",
    },
    "editor": {
        "candidates": ["kate", "kwrite", "gedit", "mousepad", "xed", "pluma", "featherpad", "geany", "leafpad", "nano"],
        "type": "bin",
        "proc": "editor",
    },
    "kate": {"candidates": ["kate"], "type": "bin", "proc": "kate"},
    "kwrite": {"candidates": ["kwrite"], "type": "bin", "proc": "kwrite"},
    "gedit": {"candidates": ["gedit"], "type": "bin", "proc": "gedit"},
    "mousepad": {"candidates": ["mousepad"], "type": "bin", "proc": "mousepad"},

    # File Manager
    "explorer": {
        "candidates": ["dolphin", "nautilus", "thunar", "nemo", "pcmanfm", "caja", "index"],
        "type": "bin",
        "proc": "dolphin",
    },
    "files": {
        "candidates": ["dolphin", "nautilus", "thunar", "nemo", "pcmanfm", "caja", "index"],
        "type": "bin",
        "proc": "dolphin",
    },
    "dolphin": {"candidates": ["dolphin"], "type": "bin", "proc": "dolphin"},
    "nautilus": {"candidates": ["nautilus"], "type": "bin", "proc": "nautilus"},
    "thunar": {"candidates": ["thunar"], "type": "bin", "proc": "thunar"},

    # Terminal
    "terminal": {
        "candidates": ["konsole", "gnome-terminal", "alacritty", "kitty", "foot", "xfce4-terminal", "terminator", "tilix", "xterm"],
        "type": "bin",
        "proc": "terminal",
    },
    "konsole": {"candidates": ["konsole"], "type": "bin", "proc": "konsole"},
    "gnome-terminal": {"candidates": ["gnome-terminal"], "type": "bin", "proc": "gnome-terminal"},
    "alacritty": {"candidates": ["alacritty"], "type": "bin", "proc": "alacritty"},
    "kitty": {"candidates": ["kitty"], "type": "bin", "proc": "kitty"},

    # Paint / Creative
    "paint": {
        "candidates": ["kolourpaint", "drawing", "pinta", "mypaint", "gimp", "krita", "inkscape"],
        "type": "bin",
        "proc": "kolourpaint",
    },
    "kolourpaint": {"candidates": ["kolourpaint"], "type": "bin", "proc": "kolourpaint"},
    "gimp": {"candidates": ["gimp"], "type": "bin", "proc": "gimp"},

    # Web Browsers
    "browser": {
        "candidates": ["chromium", "google-chrome-stable", "google-chrome", "firefox", "microsoft-edge-stable", "brave-browser", "opera", "epiphany"],
        "type": "browser",
        "proc": "browser",
    },
    "chrome": {
        "candidates": ["google-chrome-stable", "google-chrome", "chromium"],
        "type": "browser",
        "proc": "chrome",
    },
    "chromium": {"candidates": ["chromium", "chromium-browser"], "type": "browser", "proc": "chromium"},
    "firefox": {"candidates": ["firefox", "firefox-esr"], "type": "browser", "proc": "firefox"},
    "edge": {"candidates": ["microsoft-edge-stable", "microsoft-edge"], "type": "browser", "proc": "msedge"},

    # Settings & Utilities
    "settings": {
        "candidates": ["systemsettings", "gnome-control-center", "xfce4-settings-manager", "mate-control-center"],
        "type": "bin",
        "proc": "systemsettings",
    },
    "blender": {"candidates": ["blender"], "type": "bin", "proc": "blender"},
    "vlc": {"candidates": ["vlc"], "type": "bin", "proc": "vlc"},
    "canva": {"candidates": ["canva"], "type": "bin", "proc": "canva"},
}

# Compatibility dictionary mapping directly to target names
BUILTIN_APP_REGISTRY: Dict[str, Dict[str, str]] = {
    k: {"target": v["candidates"][0], "type": v["type"], "proc": v.get("proc", v["candidates"][0])}
    for k, v in BUILTIN_APP_FALLBACKS.items()
}

APP_REGISTRY: Dict[str, Dict[str, str]] = dict(BUILTIN_APP_REGISTRY)

BROWSER_CANDIDATE_PATHS: Dict[str, List[str]] = {
    "chromium": ["/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/local/bin/chromium"],
    "chrome": ["/usr/bin/google-chrome-stable", "/usr/bin/google-chrome"],
    "firefox": ["/usr/bin/firefox", "/usr/bin/firefox-esr"],
    "edge": ["/usr/bin/microsoft-edge-stable", "/usr/bin/microsoft-edge"],
}


def get_user_registry_path() -> Path:
    """Returns persistent user registry path in ~/.extra/app_registry.json."""
    p = Path.home() / ".extra"
    p.mkdir(parents=True, exist_ok=True)
    return p / "app_registry.json"


def load_user_registry(custom_path: Optional[Path] = None) -> Dict[str, Dict[str, str]]:
    """Loads custom registered applications from user JSON config."""
    reg_path = custom_path or get_user_registry_path()
    if not reg_path.exists():
        return {}
    try:
        with open(reg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, dict) and "target" in v:
                        APP_REGISTRY[k.strip().lower()] = {
                            "target": v.get("target", ""),
                            "type": v.get("type", "bin"),
                            "proc": v.get("proc", os.path.basename(v.get("target", ""))),
                        }
                return data
    except Exception:
        pass
    return {}


def register_app(
    alias: str,
    target: str,
    app_type: str = "bin",
    process_name: Optional[str] = None,
) -> bool:
    """Registers custom application alias into user registry."""
    clean_alias = alias.strip().lower()
    proc = process_name or os.path.basename(target)
    APP_REGISTRY[clean_alias] = {"target": target, "type": app_type, "proc": proc}

    reg_path = get_user_registry_path()
    existing: Dict[str, Any] = {}
    if reg_path.exists():
        try:
            with open(reg_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = {}

    existing[clean_alias] = {"target": target, "type": app_type, "proc": proc}
    try:
        with open(reg_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save user registry: {e}")
        return False


def get_registered_apps() -> Dict[str, Dict[str, str]]:
    """Returns copy of active application registry."""
    return dict(APP_REGISTRY)


def resolve_executable(app_name: str) -> Optional[Tuple[str, str]]:
    """
    Deterministically resolves an application name, alias, or generic category
    to a verified executable path and application type ('bin' | 'browser').
    """
    clean = app_name.strip().lower()
    indexer = get_desktop_indexer()

    # 1. Custom user registry lookup
    if clean in APP_REGISTRY and clean not in BUILTIN_APP_FALLBACKS:
        info = APP_REGISTRY[clean]
        target = info["target"]
        resolved = shutil.which(target) or (target if os.path.exists(target) else None)
        if resolved:
            return resolved, info.get("type", "bin")

    # 2. Semantic fallback alias resolution (intelligent multi-candidate search)
    if clean in BUILTIN_APP_FALLBACKS:
        fallback = BUILTIN_APP_FALLBACKS[clean]
        app_type = fallback.get("type", "bin")
        for candidate in fallback["candidates"]:
            # Check PATH
            which_cand = shutil.which(candidate)
            if which_cand:
                return which_cand, app_type
            # Check XDG Desktop Index
            entry = indexer.find_by_query(candidate)
            if entry and entry.executable:
                resolved_bin = shutil.which(entry.executable) or (
                    entry.executable if os.path.exists(entry.executable) else None
                )
                if resolved_bin:
                    return resolved_bin, app_type

    # 3. Direct PATH resolution
    which_path = shutil.which(app_name)
    if which_path:
        is_browser = any(b in clean for b in ("chrome", "chromium", "firefox", "edge", "browser"))
        return which_path, "browser" if is_browser else "bin"

    # 4. Direct absolute/relative filesystem path
    if os.path.isabs(app_name) and os.path.exists(app_name):
        return app_name, "bin"

    # 5. XDG Desktop Entry search
    entry = indexer.find_by_query(app_name)
    if entry and entry.executable:
        resolved_bin = shutil.which(entry.executable) or (
            entry.executable if os.path.exists(entry.executable) else None
        )
        if resolved_bin:
            is_browser = "WebBrowser" in entry.categories or any(
                b in entry.name.lower() for b in ("chrome", "chromium", "firefox", "edge", "browser")
            )
            return resolved_bin, "browser" if is_browser else "bin"

    return None


def open_uri(uri: str) -> bool:
    """Opens URL or URI protocol handler using xdg-open or gio open."""
    for cmd in ["xdg-open", "gio"]:
        if shutil.which(cmd):
            try:
                args = [cmd, "open", uri] if cmd == "gio" else [cmd, uri]
                subprocess.Popen(
                    args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                return True
            except Exception:
                pass
    return False


def launch_app(
    app_name: str,
    args: Optional[List[str]] = None,
    wait_for_window: bool = True,
    timeout: float = 5.0,
    profile: Optional[str] = None,
    maximize: bool = False,
) -> LaunchResult:
    """
    Deterministically launches application by alias or command, decoupling process
    and returning execution telemetry.
    """
    t0 = time.perf_counter()

    # URI protocol handler check
    if "://" in app_name:
        ok = open_uri(app_name)
        dt = (time.perf_counter() - t0) * 1000.0
        return LaunchResult(
            success=ok,
            app_name=app_name,
            target_executed=app_name,
            duration_ms=dt,
            message="URI dispatched" if ok else "URI dispatch failed",
        )

    resolved = resolve_executable(app_name)
    if not resolved:
        dt = (time.perf_counter() - t0) * 1000.0
        return LaunchResult(
            success=False,
            app_name=app_name,
            target_executed="",
            duration_ms=dt,
            message=f"Executable for '{app_name}' could not be resolved in PATH or XDG desktop index.",
        )

    target_exe, target_type = resolved
    cmd = [target_exe] + (args or [])

    # Browser crash bubble auto-suppression (Chromium, Edge, Chrome)
    if target_type == "browser" and "firefox" not in os.path.basename(target_exe).lower():
        suppression_flags = [
            "--no-first-run",
            "--no-default-browser-check",
            "--hide-crash-restore-bubble",
            "--force-renderer-accessibility",
        ]
        # Only inject flags if not already present
        for flag in suppression_flags:
            if flag not in cmd:
                cmd.append(flag)
        if profile:
            profile_flag = f"--profile-directory={profile}"
            if not any(a.startswith("--profile-directory") for a in cmd):
                cmd.append(profile_flag)

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        pid = proc.pid
    except Exception as e:
        dt = (time.perf_counter() - t0) * 1000.0
        return LaunchResult(
            success=False,
            app_name=app_name,
            target_executed=target_exe,
            duration_ms=dt,
            message=f"Failed to launch process: {e}",
        )

    hwnd = None
    win_title = None

    if wait_for_window:
        t_end = time.time() + timeout
        query_candidates = [app_name, os.path.basename(target_exe)]
        if target_type == "browser":
            query_candidates.extend(["chrome", "chromium", "firefox", "edge", "brave"])
        while time.time() < t_end:
            for q in query_candidates:
                win = find_window_by_title(q, timeout=0.05)
                if win:
                    hwnd = win.hwnd
                    win_title = win.title
                    break
            if hwnd:
                force_activate_window(hwnd)
                if maximize:
                    try:
                        from extra.core.platform.linux.focus import snap_window
                        snap_window(hwnd, "maximize")
                    except Exception:
                        pass
                break
            time.sleep(0.15)

    dt = (time.perf_counter() - t0) * 1000.0
    return LaunchResult(
        success=True,
        app_name=app_name,
        target_executed=target_exe,
        hwnd=hwnd,
        window_title=win_title,
        pid=pid,
        duration_ms=dt,
        message=f"Launched '{app_name}' successfully (PID: {pid}).",
    )


class LinuxShellLauncher(AbstractShellLauncher):
    """Linux implementation of AbstractShellLauncher."""

    def launch_app(
        self,
        app_name: str,
        args: Optional[List[str]] = None,
        wait_for_window: bool = True,
        timeout: float = 5.0,
        profile: Optional[str] = None,
        maximize: bool = False,
    ) -> LaunchResult:
        return launch_app(
            app_name=app_name,
            args=args,
            wait_for_window=wait_for_window,
            timeout=timeout,
            profile=profile,
            maximize=maximize,
        )

    def open_uri(self, uri: str) -> bool:
        return open_uri(uri)

    def resolve_executable(self, app_name: str) -> Optional[Tuple[str, str]]:
        return resolve_executable(app_name)


ShellLauncher = LinuxShellLauncher
