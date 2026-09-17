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
from typing import Optional, List, Dict, Any

from extra.core.platform.windows.shell import resolve_executable

logger = logging.getLogger("extra.scout.detector")


@dataclass
class AppProfile:
    """Discovered capability profile of a desktop application."""
    app_name: str
    executable_path: Optional[str] = None
    is_installed: bool = False
    ui_framework: str = "unknown"  # 'electron' | 'directx_opengl_viewport' | 'qt' | 'wpf' | 'win32' | 'uwp' | 'unknown'
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


# Known viewport applications where canvas is drawn via OpenGL/DirectX GPU shaders
VIEWPORT_APPS = {
    "blender", "blender.exe",
    "resolve", "resolve.exe", "davinci_resolve",
    "maya", "maya.exe",
    "3dsmax", "3dsmax.exe",
    "unreal", "unrealengine", "ue5",
    "unity", "unity.exe",
    "autocad", "acad.exe",
    "fusion360",
}

# Known web/electron canvas tools where UIAutomation cannot access individual canvas elements
CANVAS_ELECTRON_APPS = {
    "canva", "canva.exe",
    "figma", "figma.exe",
    "miro", "miro.exe",
    "framer", "framer.exe",
    "whimsical",
}

# Standard scripting APIs mapped by application name
SCRIPTING_API_MAP = {
    "blender": "bpy (Python 3.x embedded scripting engine)",
    "photoshop": "ExtendScript / UXP / COM: Photoshop.Application",
    "illustrator": "ExtendScript / COM: Illustrator.Application",
    "indesign": "ExtendScript / COM: InDesign.Application",
    "aftereffects": "ExtendScript / aerender CLI",
    "davinci_resolve": "DaVinciResolveScript (Python 3.x / Lua API)",
    "resolve": "DaVinciResolveScript (Python 3.x / Lua API)",
    "excel": "COM: Excel.Application / openpyxl / pandas",
    "word": "COM: Word.Application / python-docx",
    "powerpoint": "COM: PowerPoint.Application / python-pptx",
    "autocad": "AutoLISP / COM: AutoCAD.Application",
    "gimp": "Script-Fu (Scheme) / Python-Fu (Python)",
    "inkscape": "Inkscape CLI batch actions / Python extensions",
    "audacity": "mod-script-pipe (named pipe IPC)",
    "obs": "obs-websocket RPC API / CLI parameters",
    "obs-studio": "obs-websocket RPC API / CLI parameters",
    "code": "VS Code CLI / Extensions API",
    "vscode": "VS Code CLI / Extensions API",
    "canva": "Fast-Path (PIL generation + STA Clipboard paste) / REST API",
    "figma": "Fast-Path (PIL/SVG generation + STA Clipboard paste) / Plugin API",
    "notepad": "Direct File I/O (Path.write_text) + extra_launch",
    "mspaint": "PIL Image generation + extra_launch",
    "calc": "extra_type direct Win32 VK_PACKET typing",
}


def _inspect_directory_framework(dir_path: str) -> str:
    """Inspects binaries and libraries in an application directory to identify UI framework."""
    if not os.path.isdir(dir_path):
        return "unknown"

    # Check Electron indicators
    resources_dir = os.path.join(dir_path, "resources")
    if os.path.isdir(resources_dir):
        if os.path.exists(os.path.join(resources_dir, "app.asar")) or os.path.exists(os.path.join(resources_dir, "app")):
            return "electron"
    if os.path.exists(os.path.join(dir_path, "v8_context_snapshot.bin")) and os.path.exists(os.path.join(dir_path, "ffmpeg.dll")):
        return "electron"

    # Check Qt indicators
    if glob.glob(os.path.join(dir_path, "Qt5*.dll")) or glob.glob(os.path.join(dir_path, "Qt6*.dll")):
        return "qt"

    # Check WPF / .NET indicators
    if os.path.exists(os.path.join(dir_path, "wpfgfx_v0400.dll")) or os.path.exists(os.path.join(dir_path, "PresentationCore.dll")):
        return "wpf"

    return "win32"


# Known pure GUI applications that ignore CLI flags and launch GUI windows if probed
GUI_ONLY_APPS = {
    "calc", "calc.exe", "calculator", "calculatorapp.exe",
    "notepad", "notepad.exe",
    "mspaint", "mspaint.exe", "pbrush.exe",
    "explorer", "explorer.exe",
    "photos", "photos.exe",
    "snippingtool", "snippingtool.exe",
    "applicationframehost.exe",
}


def _probe_cli_help(executable: str) -> Optional[str]:
    """Runs application with --help / -h with a strict timeout to avoid blocking."""
    exe_name = os.path.basename(executable).lower()
    if exe_name in GUI_ONLY_APPS or executable.lower() in GUI_ONLY_APPS:
        return None

    flags = ["--help", "-h", "/?"]
    flags_blender = ["-b", "-h"]  # Blender needs -b to avoid launching GUI

    test_flags = flags_blender if "blender" in executable.lower() else flags

    for flag in test_flags:
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

    # 1. Resolve executable
    resolved = resolve_executable(clean_name)
    if resolved and os.path.exists(resolved):
        profile.executable_path = resolved
        profile.is_installed = True
        app_dir = os.path.dirname(resolved)

        # 2. Framework detection
        if clean_name in VIEWPORT_APPS or any(v in resolved.lower() for v in ("blender", "resolve", "maya")):
            profile.ui_framework = "directx_opengl_viewport"
            profile.notes.append("Viewport application: 3D canvas does not support Win32 UIA element clicking.")
        elif clean_name in CANVAS_ELECTRON_APPS or any(c in resolved.lower() for c in ("canva", "figma")):
            profile.ui_framework = "electron_web_canvas"
            profile.notes.append("Web/Electron canvas: Internal WebGL/DOM canvas cannot be clicked via UIA.")
        elif "windowsapps" in resolved.lower():
            profile.ui_framework = "uwp"
        else:
            profile.ui_framework = _inspect_directory_framework(app_dir)

        # 3. CLI probe
        help_text = _probe_cli_help(resolved)
        if help_text:
            profile.cli_supported = True
            profile.cli_help_text = help_text
            profile.notes.append("Application supports CLI automation.")
    else:
        # Not installed locally or web application
        profile.is_installed = False
        if clean_name in CANVAS_ELECTRON_APPS:
            profile.ui_framework = "electron_web_canvas"
        elif clean_name in VIEWPORT_APPS:
            profile.ui_framework = "directx_opengl_viewport"
        else:
            profile.ui_framework = "unknown"

    # 4. Scripting API mapping
    for key, api_name in SCRIPTING_API_MAP.items():
        if key in clean_name or (resolved and key in resolved.lower()):
            profile.scripting_api = api_name
            break

    return profile
