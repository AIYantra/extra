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

import json
from pathlib import Path

_SEEDS_CACHE: Optional[Dict[str, Dict[str, Any]]] = None


def get_knowledge_seeds() -> Dict[str, Dict[str, Any]]:
    """
    Loads application knowledge seeds dynamically from:
    1. User customization: ~/.extra/knowledge_seeds.json
    2. Package assets: extra/core/scout/knowledge_seeds.json
    3. extra/assets/scout/knowledge_seeds.json
    """
    global _SEEDS_CACHE
    if _SEEDS_CACHE is not None:
        return _SEEDS_CACHE

    paths_to_check = [
        Path.home() / ".extra" / "knowledge_seeds.json",
        Path(__file__).parent / "knowledge_seeds.json",
        Path(__file__).resolve().parent.parent.parent / "assets" / "scout" / "knowledge_seeds.json",
    ]
    for p in paths_to_check:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f_seed:
                    _SEEDS_CACHE = json.load(f_seed)
                    return _SEEDS_CACHE
            except Exception as e:
                logger.warning("Failed loading knowledge seeds from %s: %s", p, e)

    _SEEDS_CACHE = {}
    return _SEEDS_CACHE


class _LazyCuratedIntelligence(dict):
    """Backwards-compatible dictionary proxy that lazily loads external knowledge seeds."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._loaded = False

    def _ensure(self):
        if not self._loaded:
            self._loaded = True
            self.update(get_knowledge_seeds())

    def __len__(self):
        self._ensure()
        return super().__len__()

    def __iter__(self):
        self._ensure()
        return super().__iter__()

    def __getitem__(self, item):
        self._ensure()
        return super().__getitem__(item)

    def __contains__(self, item):
        self._ensure()
        return super().__contains__(item)

    def get(self, item, default=None):
        self._ensure()
        return super().get(item, default)

    def items(self):
        self._ensure()
        return super().items()

    def keys(self):
        self._ensure()
        return super().keys()

    def values(self):
        self._ensure()
        return super().values()


CURATED_INTELLIGENCE: Dict[str, Dict[str, Any]] = _LazyCuratedIntelligence()


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
