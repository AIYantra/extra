"""
Extra Scout — Application Profile & Capability Detector
Detects local executable installations, UI frameworks (Electron, Win32, Qt, WPF, OpenGL/DirectX),
CLI flags, and available scripting APIs before taking GUI actions.
"""

import os
import sys
import glob
import shutil
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any, Set

from extra.core.platform import resolve_executable

logger = logging.getLogger("extra.scout.detector")


@dataclass
class AppProfile:
    """Discovered capability profile of a desktop application."""
    app_name: str
    executable_path: Optional[str] = None
    is_installed: bool = False
    ui_framework: str = "unknown"  # 'electron' | 'electron_web_canvas' | 'directx_opengl_viewport' | 'qt' | 'wpf' | 'win32' | 'uwp' | 'unknown'
    cli_supported: bool = False
    cli_help_text: Optional[str] = None
    scripting_api: Optional[str] = None  # e.g. 'bpy', 'extendscript', 'com', 'cli', 'mod-script-pipe'
    version: Optional[str] = None
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "app_name": self.app_name,
            "executable_path": self.executable_path,
            "is_installed": self.is_installed,
            "ui_framework": self.ui_framework,
            "cli_supported": self.cli_supported,
            "cli_help_text": self.cli_help_text[:500] if self.cli_help_text else None,
            "scripting_api": self.scripting_api,
            "version": self.version,
            "notes": self.notes,
        }


def _get_seeds() -> Dict[str, Dict[str, Any]]:
    """Helper to lazily load knowledge seeds without circular imports."""
    try:
        from extra.core.scout.scraper import get_knowledge_seeds
        return get_knowledge_seeds()
    except Exception:
        return {}


class _DynamicSeedSet(set):
    """Dynamic set proxy backed by external knowledge seeds for backwards compatibility."""
    def __init__(self, filter_fn):
        super().__init__()
        self._filter_fn = filter_fn
        self._loaded = False

    def _ensure(self):
        if not self._loaded:
            self._loaded = True
            for k, v in _get_seeds().items():
                if self._filter_fn(k, v):
                    super().add(k)
                    super().add(f"{k}.exe")

    def __contains__(self, item):
        self._ensure()
        return super().__contains__(str(item).lower())

    def __iter__(self):
        self._ensure()
        return super().__iter__()

    def __len__(self):
        self._ensure()
        return super().__len__()


class _DynamicScriptingMap(dict):
    """Dynamic scripting map backed by external knowledge seeds for backwards compatibility."""
    def __init__(self):
        super().__init__()
        self._loaded = False

    def _ensure(self):
        if not self._loaded:
            self._loaded = True
            for k, v in _get_seeds().items():
                api = v.get("scripting_api")
                if api:
                    super().__setitem__(k, api)

    def get(self, item, default=None):
        self._ensure()
        return super().get(item, default)

    def __getitem__(self, item):
        self._ensure()
        return super().__getitem__(item)

    def __contains__(self, item):
        self._ensure()
        return super().__contains__(item)

    def items(self):
        self._ensure()
        return super().items()

    def keys(self):
        self._ensure()
        return super().keys()

    def values(self):
        self._ensure()
        return super().values()


# Backward-compatible proxies populated dynamically from external knowledge seeds
VIEWPORT_APPS: Set[str] = _DynamicSeedSet(
    lambda k, v: v.get("ui_framework") == "directx_opengl_viewport"
)
CANVAS_ELECTRON_APPS: Set[str] = _DynamicSeedSet(
    lambda k, v: v.get("ui_framework") == "electron_web_canvas"
)
SCRIPTING_API_MAP: Dict[str, str] = _DynamicScriptingMap()

# Backward-compatible set for Windows GUI-only applets
GUI_ONLY_APPS: Set[str] = {
    "calc", "calc.exe", "calculator", "calculatorapp.exe",
    "notepad", "notepad.exe",
    "mspaint", "mspaint.exe", "pbrush.exe",
    "explorer", "explorer.exe",
    "photos", "photos.exe",
    "snippingtool", "snippingtool.exe",
    "applicationframehost.exe",
}


def _is_windows_system_gui(executable: str) -> bool:
    """
    Checks if an executable is a Windows built-in system GUI tool
    that should not be probed with Unix-style --help flags.
    """
    sys_root = os.environ.get("SystemRoot", r"C:\Windows").lower()
    exe_lower = executable.lower()

    if exe_lower.startswith(sys_root):
        basename = os.path.basename(exe_lower)
        if basename in ("cmd.exe", "powershell.exe", "wt.exe"):
            return False
        if "system32" in exe_lower or "systemapps" in exe_lower or basename == "explorer.exe":
            return True

    if "windowsapps" in exe_lower:
        return True

    return False


def _inspect_directory_framework(dir_path: str) -> str:
    """Inspects binaries and libraries in an application directory to identify UI framework."""
    if not os.path.isdir(dir_path):
        return "unknown"

    # 1. Check Electron indicators
    resources_dir = os.path.join(dir_path, "resources")
    if os.path.isdir(resources_dir):
        if os.path.exists(os.path.join(resources_dir, "app.asar")) or os.path.exists(os.path.join(resources_dir, "app")):
            return "electron"
    if os.path.exists(os.path.join(dir_path, "v8_context_snapshot.bin")) and (
        os.path.exists(os.path.join(dir_path, "ffmpeg.dll")) or os.path.exists(os.path.join(dir_path, "chrome_elf.dll"))
    ):
        return "electron"

    # 2. Check 3D Viewport / CAD GPU shader libraries (DirectX / OpenGL / Vulkan / OpenUSD)
    viewport_dlls = [
        "opengl32.dll", "vulkan-1.dll", "glew32.dll", "glfw3.dll", "nvoglv64.dll",
        "OpenColorIO*.dll", "OpenImageIO*.dll", "tbb.dll",
    ]
    for pattern in viewport_dlls:
        if "*" in pattern:
            if glob.glob(os.path.join(dir_path, pattern)) or glob.glob(os.path.join(dir_path, "bin", pattern)):
                return "directx_opengl_viewport"
        else:
            if os.path.exists(os.path.join(dir_path, pattern)) or os.path.exists(os.path.join(dir_path, "bin", pattern)):
                return "directx_opengl_viewport"

    # 3. Check Qt indicators
    if (
        glob.glob(os.path.join(dir_path, "Qt5*.dll"))
        or glob.glob(os.path.join(dir_path, "Qt6*.dll"))
        or glob.glob(os.path.join(dir_path, "bin", "Qt*.dll"))
    ):
        return "qt"

    # 4. Check WPF / .NET indicators
    if (
        os.path.exists(os.path.join(dir_path, "wpfgfx_v0400.dll"))
        or os.path.exists(os.path.join(dir_path, "PresentationCore.dll"))
    ):
        return "wpf"

    return "win32"


def _detect_embedded_scripting_api(dir_path: str) -> Optional[str]:
    """Detects embedded Python, Lua, or script engines inside application directory."""
    if not os.path.isdir(dir_path):
        return None
    if glob.glob(os.path.join(dir_path, "python3*.dll")) or glob.glob(os.path.join(dir_path, "python", "python*.exe")):
        return "Embedded Python 3.x Scripting Engine"
    if glob.glob(os.path.join(dir_path, "lua*.dll")):
        return "Embedded Lua Scripting Engine"
    return None


def _probe_cli_help(executable: str, custom_flags: Optional[List[str]] = None) -> Optional[str]:
    """Runs application with --help / -h with a strict timeout to avoid blocking."""
    exe_name = os.path.basename(executable).lower()
    if exe_name in GUI_ONLY_APPS or _is_windows_system_gui(executable):
        return None

    flags = custom_flags if custom_flags else ["--help", "-h", "/?"]

    for flag in flags:
        try:
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            proc = subprocess.run(
                [executable, flag],
                capture_output=True,
                text=True,
                timeout=1.5,
                startupinfo=startupinfo,
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            if len(out.strip()) > 20:
                return out.strip()
        except Exception:
            continue

    return None


def detect_app_profile(app_name: str) -> AppProfile:
    """
    Detects executable path, UI framework, CLI parameters, and scripting capabilities
    for the specified desktop application.
    """
    clean_name = app_name.strip().lower()
    profile = AppProfile(app_name=clean_name)

    # 1. Resolve executable dynamically
    resolved = resolve_executable(clean_name)
    app_dir = None
    seed_data = None

    # Load seed intelligence if available
    seeds = _get_seeds()
    for k, v in seeds.items():
        if k == clean_name or (resolved and k in resolved.lower()):
            seed_data = v
            break

    custom_probe_flags = seed_data.get("cli_probe_flags") if seed_data else None

    if resolved and os.path.exists(resolved):
        profile.executable_path = resolved
        profile.is_installed = True
        app_dir = os.path.dirname(resolved)

        # 2. Dynamic framework detection from directory / binaries
        if "windowsapps" in resolved.lower():
            profile.ui_framework = "uwp"
        else:
            profile.ui_framework = _inspect_directory_framework(app_dir)

        # Dynamic scripting API discovery
        detected_script = _detect_embedded_scripting_api(app_dir)
        if detected_script:
            profile.scripting_api = detected_script

        # 3. CLI probe (skips system GUI applets universally)
        help_text = _probe_cli_help(resolved, custom_flags=custom_probe_flags)
        if help_text:
            profile.cli_supported = True
            profile.cli_help_text = help_text
            profile.notes.append("Application supports CLI automation.")
    else:
        profile.is_installed = False
        profile.ui_framework = "unknown"

    # 4. Enrich profile with external declarative seeds
    if seed_data:
        # If framework is generic or uninstalled, adopt seed's specialized framework
        if profile.ui_framework in ("unknown", "electron", "win32") and seed_data.get("ui_framework"):
            profile.ui_framework = seed_data["ui_framework"]

        # Note caveats
        if profile.ui_framework == "directx_opengl_viewport":
            profile.notes.append("Viewport application: 3D canvas does not support Win32 UIA element clicking.")
        elif profile.ui_framework == "electron_web_canvas":
            profile.notes.append("Web/Electron canvas: Internal WebGL/DOM canvas cannot be clicked via UIA.")
        elif seed_data.get("ui_surface_caveat") and seed_data["ui_surface_caveat"] not in profile.notes:
            profile.notes.append(seed_data["ui_surface_caveat"])

        # Scripting API fallback
        if not profile.scripting_api and seed_data.get("scripting_api"):
            profile.scripting_api = seed_data["scripting_api"]

    return profile
