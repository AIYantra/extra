"""
Extra Scout — Cheat Sheet, Hotkey, and Documentation Scraper
Provides curated high-density intelligence for creative/pro apps and lightweight web search fallback.
"""

import re
import urllib.request
import urllib.parse
import html
import logging
from typing import Dict, Any, List, Optional
from extra.core.scout.detector import AppProfile

logger = logging.getLogger("extra.scout.scraper")

# Curated high-density intelligence for pro applications
CURATED_INTELLIGENCE: Dict[str, Dict[str, Any]] = {
    "blender": {
        "summary": "3D creation suite with OpenGL viewport and full embedded Python bpy API.",
        "ui_surface_caveat": "DirectX/OpenGL viewport renders internally; UIAutomation cannot click 3D mesh elements. Never spend turns coordinate clicking in the 3D space.",
        "fast_paths": [
            "Scripting Fast-Path: Use headless Python bpy automation `blender.exe -b --python script.py` to create meshes, modify materials, and render frames without GUI latency.",
            "Visual Verification: Launch GUI `extra_launch(app_name='blender', args=[file_path])` then take single `extra_screenshot()` to present.",
            "Scene Navigation: Use standard Viewport Numpad hotkeys instead of mouse panning.",
        ],
        "hotkeys": [
            {"key": "Tab", "action": "Toggle Edit Mode / Object Mode", "category": "Modes"},
            {"key": "Shift + A", "action": "Add Mesh / Object / Light menu", "category": "Creation"},
            {"key": "G", "action": "Grab / Translate selected object", "category": "Transform"},
            {"key": "R", "action": "Rotate selected object", "category": "Transform"},
            {"key": "S", "action": "Scale selected object", "category": "Transform"},
            {"key": "X", "action": "Delete selected object", "category": "Edit"},
            {"key": "F12", "action": "Render still frame", "category": "Render"},
            {"key": "Ctrl + F12", "action": "Render animation", "category": "Render"},
            {"key": "Numpad 1", "action": "Front Orthographic View", "category": "Navigation"},
            {"key": "Numpad 3", "action": "Right Orthographic View", "category": "Navigation"},
            {"key": "Numpad 7", "action": "Top Orthographic View", "category": "Navigation"},
            {"key": "Ctrl + Alt + Numpad 0", "action": "Align Active Camera to Current View", "category": "Camera"},
            {"key": "Z", "action": "Shading Pie Menu (Solid / Wireframe / Rendered)", "category": "Viewport"},
        ],
        "cli_options": [
            {"flag": "-b, --background", "description": "Run in background without GUI", "example": "blender.exe -b scene.blend -f 1"},
            {"flag": "-P, --python <file>", "description": "Run specified Python script file", "example": "blender.exe -b --python generate.py"},
            {"flag": "-o, --render-output <path>", "description": "Set output path for renders", "example": "blender.exe -b scene.blend -o //render_ -F PNG -f 1"},
            {"flag": "-f <frame>", "description": "Render single frame", "example": "blender.exe -b scene.blend -f 1"},
        ],
        "anti_stall_guardrails": [
            "NEVER try to click 3D mesh vertices or object centers with mouse coordinates.",
            "Use bpy scripts in `%USERPROFILE%\\.extra\\workspace\\` to execute procedural modeling.",
            "Dismiss splash screen with Esc or Space if present.",
        ],
    },
    "photoshop": {
        "summary": "Digital image editing and raster design suite with ExtendScript and UXP APIs.",
        "ui_surface_caveat": "Canvas layers are GPU-composited and do not expose individual layer UIAutomation elements.",
        "fast_paths": [
            "Asset Generation: Generate base imagery via PIL / Python, then open in Photoshop: `extra_launch(app_name='photoshop', args=[safe_png_path])`.",
            "ExtendScript Fast-Path: Write a `.jsx` automation script and execute via COM `Photoshop.Application.DoJavaScript(file)`. Allows silent layer manipulation and exporting.",
            "Clipboard Fast-Path: Copy raster images to clipboard via PowerShell STA and paste directly into canvas (`Ctrl + V`).",
        ],
        "hotkeys": [
            {"key": "V", "action": "Move Tool", "category": "Tools"},
            {"key": "M", "action": "Marquee Selection Tool", "category": "Tools"},
            {"key": "B", "action": "Brush Tool", "category": "Tools"},
            {"key": "T", "action": "Horizontal Type Tool", "category": "Tools"},
            {"key": "Ctrl + J", "action": "Duplicate Layer / Selection", "category": "Layers"},
            {"key": "Ctrl + Shift + N", "action": "Create New Layer dialog", "category": "Layers"},
            {"key": "Ctrl + Alt + Shift + S", "action": "Save for Web (Legacy)", "category": "Export"},
            {"key": "Ctrl + Alt + S", "action": "Save a Copy dialog", "category": "Export"},
            {"key": "Ctrl + Z", "action": "Undo / Redo", "category": "Edit"},
            {"key": "Ctrl + 0", "action": "Fit On Screen", "category": "Navigation"},
        ],
        "cli_options": [
            {"flag": "<file_path>", "description": "Open image or PSD directly", "example": "photoshop.exe design.psd"},
        ],
        "anti_stall_guardrails": [
            "Avoid clicking individual color picker swatches or small layer icons.",
            "Dismiss modal dialogs with Esc or Enter.",
            "Save files to `%USERPROFILE%\\.extra\\workspace\\` to avoid Controlled Folder Access blockages.",
        ],
    },
    "canva": {
        "summary": "Web/Electron-based design suite rendering into an HTML5/WebGL canvas element.",
        "ui_surface_caveat": "Electron shell: Top search bar ('What would you like to create?'), category icons, and left sidebar are standard clickable web elements. Only the inner canvas drawing viewport renders in WebGL/HTML5 without Win32 accessibility nodes.",
        "fast_paths": [
            "Native Template Fast-Path: On the Canva home screen, click the visible category icons (e.g. 'Presentation', 'Instagram Post') or click the prominent search bar 'What would you like to create?', type the topic, press Enter, and click a template card to open and edit.",
            "Clipboard Fast-Path (Rapid Custom Assets): Generate pixel-perfect graphics programmatically to disk via Python (PIL) inside `%USERPROFILE%\\.extra\\workspace\\<name>.png`. Copy to Windows Clipboard via PowerShell STA, focus Canva (`extra_focus_window(window_title='Canva')`), click the canvas viewport, and paste instantly (`Ctrl + V`).",
            "Canvas Elements Hotkeys: When the design canvas is open, press `T` for Text, `R` for Rectangle, `C` for Circle, `L` for Line.",
        ],
        "hotkeys": [
            {"key": "T", "action": "Add Text Box to canvas", "category": "Elements"},
            {"key": "R", "action": "Add Rectangle to canvas", "category": "Elements"},
            {"key": "C", "action": "Add Circle to canvas", "category": "Elements"},
            {"key": "L", "action": "Add Line to canvas", "category": "Elements"},
            {"key": "Ctrl + V", "action": "Paste image/text directly from clipboard onto canvas", "category": "Edit"},
            {"key": "Ctrl + G", "action": "Group selected elements", "category": "Organization"},
            {"key": "Ctrl + Shift + G", "action": "Ungroup selected elements", "category": "Organization"},
            {"key": "Ctrl + [", "action": "Send element backward", "category": "Arrangement"},
            {"key": "Ctrl + ]", "action": "Send element forward", "category": "Arrangement"},
        ],
        "cli_options": [],
        "anti_stall_guardrails": [
            "CRITICAL CAVEAT ON Ctrl + N: Pressing Ctrl + N in Canva desktop often defaults focus to the 'Open a design link:' field. If 'Please enter a valid design link' appears, press Esc immediately to dismiss and use the home screen search bar or category icons.",
            "ZERO Panic Scripting: Never write ad-hoc ctypes mouse or keyboard scripts. Use Extra MCP tools directly.",
            "Honoring Intent: When the user asks for Canva templates, use Canva's native search bar and template gallery instead of forcing custom script generation.",
        ],
    },
    "figma": {
        "summary": "Collaborative vector design tool built on WebGL / WebAssembly canvas.",
        "ui_surface_caveat": "Canvas objects are rendered via WebGL in WebAssembly. UIAutomation plane cannot traverse frames, shapes, or text layers inside the canvas.",
        "fast_paths": [
            "Direct Clipboard Injection: Render SVG or high-res PNG with Python PIL/svgwrite to `%USERPROFILE%\\.extra\\workspace\\`, copy to clipboard via PowerShell STA, focus Figma, and paste with `Ctrl + V`.",
            "Frame Creation: Use hotkey `F` followed by canvas click to drop a frame, or paste vector directly.",
        ],
        "hotkeys": [
            {"key": "F", "action": "Frame Tool", "category": "Tools"},
            {"key": "R", "action": "Rectangle Tool", "category": "Tools"},
            {"key": "O", "action": "Ellipse Tool", "category": "Tools"},
            {"key": "T", "action": "Text Tool", "category": "Tools"},
            {"key": "V", "action": "Move / Select Tool", "category": "Tools"},
            {"key": "Shift + A", "action": "Add Auto Layout", "category": "Layout"},
            {"key": "Ctrl + Alt + C", "action": "Copy Properties", "category": "Styling"},
            {"key": "Ctrl + Alt + V", "action": "Paste Properties", "category": "Styling"},
            {"key": "Ctrl + G", "action": "Group Selection", "category": "Organization"},
            {"key": "Ctrl + Shift + G", "action": "Ungroup Selection", "category": "Organization"},
            {"key": "Shift + 1", "action": "Zoom to Fit", "category": "Navigation"},
            {"key": "Shift + 2", "action": "Zoom to Selection", "category": "Navigation"},
        ],
        "cli_options": [],
        "anti_stall_guardrails": [
            "Never attempt coordinate clicks on the internal layer tree or canvas canvas.",
            "Inject designs via clipboard for 100% precision.",
        ],
    },
    "davinci_resolve": {
        "summary": "Non-linear video editor, color grader, and audio post-production suite.",
        "ui_surface_caveat": "Heavy Qt/DirectX interface with custom drawn controls. Complex timeline scrubbing is unreliable via mouse drag.",
        "fast_paths": [
            "Scripting API: Use DaVinciResolveScript Python library (`import DaVinciResolveScript as dvr_script; resolve = dvr_script.scriptapp('Resolve')`). Allows programmatic timeline generation, clip import, and rendering.",
            "Page Hotkeys: Switch workspaces using native page shortcuts (Shift+2 to Shift+8) rather than clicking bottom tabs.",
        ],
        "hotkeys": [
            {"key": "Shift + 2", "action": "Switch to Media Page", "category": "Pages"},
            {"key": "Shift + 3", "action": "Switch to Cut Page", "category": "Pages"},
            {"key": "Shift + 4", "action": "Switch to Edit Page", "category": "Pages"},
            {"key": "Shift + 5", "action": "Switch to Fusion Page", "category": "Pages"},
            {"key": "Shift + 6", "action": "Switch to Color Page", "category": "Pages"},
            {"key": "Shift + 7", "action": "Switch to Fairlight Audio Page", "category": "Pages"},
            {"key": "Shift + 8", "action": "Switch to Deliver / Export Page", "category": "Pages"},
            {"key": "B", "action": "Blade Tool", "category": "Editing"},
            {"key": "A", "action": "Selection Arrow Tool", "category": "Editing"},
            {"key": "Space", "action": "Play / Stop playback", "category": "Playback"},
            {"key": "J / K / L", "action": "Reverse / Pause / Forward Shuttling", "category": "Playback"},
            {"key": "Ctrl + B", "action": "Split Clip at Playhead", "category": "Editing"},
        ],
        "cli_options": [],
        "anti_stall_guardrails": [
            "Do not drag timeline playheads with mouse coords; use J/K/L and arrow keys for frame stepping.",
        ],
    },
    "inkscape": {
        "summary": "Vector graphics editor with complete command line export capability.",
        "ui_surface_caveat": "Canvas handles can be tiny; CLI flags provide instant rendering.",
        "fast_paths": [
            "CLI Export Fast-Path: Run `inkscape <file.svg> --export-filename=<out.png> --export-dpi=300` to produce high-res graphics silently in milliseconds.",
            "Vector Generation: Generate SVG files directly with Python, then open or convert via Inkscape CLI.",
        ],
        "hotkeys": [
            {"key": "F1", "action": "Select and Transform", "category": "Tools"},
            {"key": "F2", "action": "Edit paths by nodes", "category": "Tools"},
            {"key": "F4", "action": "Create Rectangles", "category": "Tools"},
            {"key": "F5", "action": "Create Ellipses", "category": "Tools"},
            {"key": "Shift + Ctrl + E", "action": "Export PNG Dialog", "category": "Export"},
            {"key": "Ctrl + Shift + C", "action": "Convert Object to Path", "category": "Paths"},
        ],
        "cli_options": [
            {"flag": "--export-filename=<path>", "description": "Exports file to PNG/PDF/SVG", "example": "inkscape file.svg --export-filename=out.png"},
            {"flag": "--export-dpi=<dpi>", "description": "Resolution for raster export", "example": "inkscape file.svg -o out.png --export-dpi=300"},
            {"flag": "--export-area-drawing", "description": "Export only drawing bounds", "example": "inkscape file.svg -o out.png -D"},
        ],
        "anti_stall_guardrails": [
            "Prefer CLI export over navigating file export dialogs.",
        ],
    },
    "obs_studio": {
        "summary": "Live video streaming and recording software with WebSocket RPC API.",
        "ui_surface_caveat": "Preview window is a DirectX/OpenGL surface.",
        "fast_paths": [
            "WebSocket API: Connect to `ws://localhost:4455` using `obsws-python` for programmatic scene switching, source muting, and recording triggers.",
            "CLI Startup: Use CLI arguments to launch directly into recording or specific profiles.",
        ],
        "hotkeys": [
            {"key": "F10", "action": "Default Start/Stop Recording (if configured)", "category": "Capture"},
        ],
        "cli_options": [
            {"flag": "--startrecording", "description": "Starts recording immediately on launch", "example": "obs64.exe --startrecording"},
            {"flag": "--startstreaming", "description": "Starts streaming immediately on launch", "example": "obs64.exe --startstreaming"},
            {"flag": "--collection <name>", "description": "Loads specific scene collection", "example": "obs64.exe --collection 'Main'"},
            {"flag": "--profile <name>", "description": "Loads specific profile", "example": "obs64.exe --profile '1080p60'"},
        ],
        "anti_stall_guardrails": [
            "Use CLI flags for recording triggers instead of searching for UI buttons in dark theme.",
        ],
    },
    "audacity": {
        "summary": "Audio recording and editing application with mod-script-pipe IPC.",
        "ui_surface_caveat": "Audio waveforms cannot be clicked with precision.",
        "fast_paths": [
            "Script Pipe API: Send commands to named pipe `\\\\.\\pipe\\ToSrvPipe` for headless effects and exports.",
            "Python Sound Gen: Generate WAV files via `pydub` or `scipy.io.wavfile` in `%USERPROFILE%\\.extra\\workspace\\`, then open in Audacity.",
        ],
        "hotkeys": [
            {"key": "Space", "action": "Play / Stop", "category": "Playback"},
            {"key": "R", "action": "Record", "category": "Recording"},
            {"key": "Shift + R", "action": "Record onto New Track", "category": "Recording"},
            {"key": "Ctrl + B", "action": "Add Label at Selection", "category": "Labels"},
            {"key": "Ctrl + Shift + E", "action": "Export Audio", "category": "Export"},
        ],
        "cli_options": [],
        "anti_stall_guardrails": [
            "Avoid dragging waveform selections; use keyboard shortcuts or pipe scripts.",
        ],
    },
    "code": {
        "summary": "VS Code source code editor with rich CLI arguments.",
        "ui_surface_caveat": "Editor rendered via Electron Monaco. Use keyboard navigation.",
        "fast_paths": [
            "CLI Fast-Path: `code -g <file>:<line>:<col>` to jump directly to code locations.",
            "Diff Viewer: `code --diff <file1> <file2>` to present visual diffs.",
        ],
        "hotkeys": [
            {"key": "Ctrl + P", "action": "Quick Open / Go to File", "category": "Navigation"},
            {"key": "Ctrl + Shift + P", "action": "Show All Commands (Command Palette)", "category": "General"},
            {"key": "Ctrl + `", "action": "Toggle Integrated Terminal", "category": "View"},
            {"key": "Ctrl + \\", "action": "Split Editor", "category": "Editor"},
            {"key": "Alt + Up/Down", "action": "Move Line Up / Down", "category": "Editing"},
            {"key": "Ctrl + /", "action": "Toggle Line Comment", "category": "Editing"},
        ],
        "cli_options": [
            {"flag": "-g, --goto <file:line[:character]>", "description": "Open file at specific line", "example": "code -g app.py:42"},
            {"flag": "-d, --diff <file1> <file2>", "description": "Compare two files", "example": "code --diff old.txt new.txt"},
            {"flag": "-r, --reuse-window", "description": "Force open in existing window", "example": "code -r workspace/"},
        ],
        "anti_stall_guardrails": [
            "Use `Ctrl + Shift + P` to trigger extensions and settings rather than hunting menu items.",
        ],
    },
    "calc": {
        "summary": "Windows Calculator with instant Win32 VK_PACKET input support.",
        "ui_surface_caveat": "Rejects clipboard paste with 'Invalid input'. UIAutomation button clicking in loops is extremely slow.",
        "fast_paths": [
            "Direct Typing Fast-Path: Launch `extra_launch(app_name='calc')`, focus `extra_focus_window(window_title='Calculator')`, and type `extra_type(text='<formula>=')`. Calculates in < 1ms.",
            "Result Presentation: Call `extra_screenshot()` once to display the final result. Never use UI inspection loops.",
        ],
        "hotkeys": [
            {"key": "Esc", "action": "Clear (C)", "category": "Calculation"},
            {"key": "Delete", "action": "Clear Entry (CE)", "category": "Calculation"},
            {"key": "F9", "action": "Toggle +/- (Negate)", "category": "Calculation"},
            {"key": "Alt + 1", "action": "Standard Mode", "category": "Modes"},
            {"key": "Alt + 2", "action": "Scientific Mode", "category": "Modes"},
            {"key": "Alt + 3", "action": "Programmer Mode", "category": "Modes"},
        ],
        "cli_options": [],
        "anti_stall_guardrails": [
            "NEVER pass `use_clipboard=True` in Calculator.",
            "NEVER call `extra_click_element` in a loop to press individual digit buttons.",
        ],
    },
    "notepad": {
        "summary": "Windows text editor for notes, briefings, and summaries.",
        "ui_surface_caveat": "Character-by-character typing of long reports takes 30+ seconds and is error-prone.",
        "fast_paths": [
            "File Injection Fast-Path: Write document directly to disk via `Path.write_text` in `%USERPROFILE%\\.extra\\workspace\\<name>.txt`.",
            "Visibly launch Notepad with the file: `extra_launch(app_name='notepad', args=[path])`.",
            "Snap to right half using `extra_hotkey(keys=['win', 'right'])` then `extra_hotkey(keys=['esc'])`.",
        ],
        "hotkeys": [
            {"key": "Ctrl + S", "action": "Save", "category": "File"},
            {"key": "Ctrl + Shift + S", "action": "Save As", "category": "File"},
            {"key": "Ctrl + F", "action": "Find text", "category": "Edit"},
            {"key": "Ctrl + H", "action": "Replace text", "category": "Edit"},
            {"key": "F5", "action": "Insert current Time/Date", "category": "Edit"},
        ],
        "cli_options": [
            {"flag": "<file_path>", "description": "Opens text file directly", "example": "notepad.exe report.txt"},
        ],
        "anti_stall_guardrails": [
            "NEVER type full documents using `extra_type`. Always write file first then launch.",
            "NEVER write to `%USERPROFILE%\\Documents` (Controlled Folder Access block).",
        ],
    },
    "mspaint": {
        "summary": "Windows graphics editor for diagrams, sketches, and charts.",
        "ui_surface_caveat": "Freehand mouse dragging results in sloppy, illegible diagrams and triggers stall breakers.",
        "fast_paths": [
            "Programmatic Render Fast-Path: Generate clean PNG chart/diagram using Python PIL or matplotlib to `%USERPROFILE%\\.extra\\workspace\\<name>.png`.",
            "Visibly open Paint with the generated image: `extra_launch(app_name='mspaint', args=[path])`.",
            "Snap to left half using `extra_hotkey(keys=['win', 'left'])` then `extra_hotkey(keys=['esc'])`.",
        ],
        "hotkeys": [
            {"key": "Ctrl + E", "action": "Image Properties dialog", "category": "Image"},
            {"key": "Ctrl + W", "action": "Resize and Skew dialog", "category": "Image"},
            {"key": "Ctrl + PageUp", "action": "Zoom In", "category": "View"},
            {"key": "Ctrl + PageDown", "action": "Zoom Out", "category": "View"},
            {"key": "Ctrl + A", "action": "Select All", "category": "Edit"},
        ],
        "cli_options": [
            {"flag": "<file_path>", "description": "Opens image file directly", "example": "mspaint.exe diagram.png"},
        ],
        "anti_stall_guardrails": [
            "NEVER attempt freehand mouse drawing. Always generate PNG via code.",
            "NEVER save to `%USERPROFILE%\\Pictures` (Controlled Folder Access block).",
        ],
    },
}


def _query_web_cheat_sheet(app_name: str) -> Optional[Dict[str, Any]]:
    """Lightweight web search retrieval fallback for unfamiliar applications."""
    try:
        query = f"{app_name} keyboard shortcuts command line cheat sheet"
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
        with urllib.request.urlopen(req, timeout=3.0) as response:
            html_content = response.read().decode("utf-8", errors="ignore")

        # Extract text snippets
        snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', html_content, re.DOTALL)
        clean_snippets = [html.unescape(re.sub(r'<[^>]+>', '', s)).strip() for s in snippets[:4]]

        if clean_snippets:
            # Parse extracted hotkey patterns e.g. Ctrl + X, Alt + F
            discovered_hotkeys = []
            for text in clean_snippets:
                matches = re.findall(r'\b(Ctrl|Alt|Shift|Cmd|Win)\s*\+\s*([A-Za-z0-9]+)\b', text)
                for mod, key in matches:
                    hk = f"{mod} + {key.upper()}"
                    if not any(item["key"] == hk for item in discovered_hotkeys):
                        discovered_hotkeys.append({
                            "key": hk,
                            "action": "Web discovered shortcut",
                            "category": "General",
                        })

            return {
                "summary": f"Web-scouted cheat sheet for {app_name}.",
                "ui_surface_caveat": "External application: verify viewport and canvas support before coordinate clicking.",
                "fast_paths": [
                    f"Check if {app_name} supports direct CLI arguments or file association opening.",
                    "Use native keyboard shortcuts where possible instead of blind clicking.",
                ],
                "hotkeys": discovered_hotkeys[:8],
                "cli_options": [],
                "anti_stall_guardrails": [
                    "Dismiss unexpected popups with Esc.",
                    "Save all output files in `%USERPROFILE%\\.extra\\workspace\\`.",
                ],
            }
    except Exception as e:
        logger.debug("Web scouting query failed or timed out: %s", e)

    return None


def get_app_intelligence(app_name: str, profile: AppProfile) -> Dict[str, Any]:
    """
    Retrieves high-density cheat sheets, CLI options, and fast paths for the given application.
    Checks curated knowledge base first, falls back to web retrieval, and defaults to framework heuristics.
    """
    clean = app_name.strip().lower()

    # Match in curated knowledge base
    for key, data in CURATED_INTELLIGENCE.items():
        if key == clean or key in clean or (profile.executable_path and key in profile.executable_path.lower()):
            return data

    # Try web retrieval if online
    web_data = _query_web_cheat_sheet(clean)
    if web_data and web_data.get("hotkeys"):
        return web_data

    # Framework-based heuristic fallback
    fw = profile.ui_framework
    if fw == "electron_web_canvas":
        return {
            "summary": f"{app_name} (Electron/Web Canvas application).",
            "ui_surface_caveat": "Internal WebGL/HTML5 canvas cannot be clicked via UIAutomation. Never spend turns coordinate hunting.",
            "fast_paths": [
                "Generate design assets via Python (PIL/SVG) inside `%USERPROFILE%\\.extra\\workspace\\`.",
                "Copy to Windows clipboard via PowerShell STA and paste into application with `Ctrl + V`.",
            ],
            "hotkeys": [
                {"key": "Ctrl + V", "action": "Paste from Clipboard", "category": "Edit"},
                {"key": "Ctrl + Z", "action": "Undo", "category": "Edit"},
                {"key": "Ctrl + S", "action": "Save", "category": "File"},
                {"key": "Esc", "action": "Dismiss Popups / Menus", "category": "Navigation"},
            ],
            "cli_options": [],
            "anti_stall_guardrails": [
                "Never attempt coordinate clicks on internal canvas graphics.",
                "Always generate assets to disk and inject via clipboard.",
            ],
        }
    elif fw == "directx_opengl_viewport":
        return {
            "summary": f"{app_name} (DirectX/OpenGL 3D/Media Viewport application).",
            "ui_surface_caveat": "Viewport is rendered by GPU shaders and does not expose UIAutomation elements.",
            "fast_paths": [
                "Use scripting APIs (Python/CLI) for procedural scene generation where supported.",
                "Rely strictly on keyboard shortcuts for navigation and transformation.",
            ],
            "hotkeys": [
                {"key": "Space", "action": "Playback / Primary Action", "category": "General"},
                {"key": "Ctrl + Z", "action": "Undo", "category": "Edit"},
                {"key": "Esc", "action": "Cancel / Deselect", "category": "Navigation"},
            ],
            "cli_options": [],
            "anti_stall_guardrails": [
                "Never click inside the 3D or media viewport without explicit hotkeys.",
            ],
        }

    # Standard Win32 / Desktop fallback
    return {
        "summary": f"{app_name} (Standard Desktop application).",
        "ui_surface_caveat": "Standard UI elements are inspectable via UIAutomation (`extra_inspect_ui`).",
        "fast_paths": [
            f"Launch directly with `extra_launch(app_name='{app_name}')`.",
            "Inspect accessible buttons with `extra_inspect_ui` and click via `extra_click_element`.",
        ],
        "hotkeys": [
            {"key": "Ctrl + S", "action": "Save", "category": "File"},
            {"key": "Ctrl + O", "action": "Open", "category": "File"},
            {"key": "Ctrl + W", "action": "Close", "category": "File"},
            {"key": "Esc", "action": "Dismiss Dialog / Popup", "category": "Navigation"},
        ],
        "cli_options": [],
        "anti_stall_guardrails": [
            "Use keyboard navigation (`Tab`, `Enter`, `Esc`) when buttons are partially obscured.",
        ],
    }
