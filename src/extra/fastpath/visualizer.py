"""
Project Extra — Dual-Plane "Glass & Engine" Visualizer Subsystem
Brings headless CLI-Anything generated artifacts live onto the physical desktop display.
Coordinates artifact detection, OS application launch, window activation, SOUL visual settle,
and ambient indicators with zero application-specific hardcoding.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from extra.fastpath.shell import launch_app, open_uri, resolve_executable
from extra.core.platform import (
    ensure_dpi_aware,
    attach_input_desktop,
    force_activate_window,
    get_foreground_window,
    list_windows,
)

logger = logging.getLogger("Extra-FastPath-Visualizer")

# Known visual, project, and document extensions prioritized for desktop presentation
PRIORITY_PROJECT_EXTENSIONS: Set[str] = {
    # 3D, CAD & Vector
    ".blend", ".fcstd", ".3mf", ".step", ".stp", ".stl", ".obj", ".svg",
    # Images & Bitmaps
    ".xcf", ".kra", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif",
    # Video & Audio
    ".mp4", ".mkv", ".webm", ".avi", ".mov", ".wav", ".mp3", ".flac",
    # Documents & Spreadsheets
    ".pdf", ".odt", ".ods", ".odp", ".docx", ".xlsx", ".pptx", ".html",
    # Diagrams & Notes
    ".drawio", ".sketch", ".canvas", ".md",
}


class DualPlaneVisualizer:
    """
    Orchestrates the transition from Plane 2 (Headless CLI) to Plane 1 (Live Glass).
    Follows the Universal Engine Invariant: ZERO hardcoded application logic.
    """

    @staticmethod
    def find_target_artifact(
        artifacts_created: List[str],
        data: Optional[Any] = None,
        args: Optional[List[str]] = None,
    ) -> Optional[Path]:
        """
        Identifies the primary artifact file to display on screen from execution outputs.
        """
        # 1. Inspect newly created files detected on disk
        candidates: List[Path] = []
        for art_path in artifacts_created:
            p = Path(art_path)
            if p.is_file():
                candidates.append(p)

        # Prioritize files by extension
        for p in candidates:
            if p.suffix.lower() in PRIORITY_PROJECT_EXTENSIONS:
                return p

        if candidates:
            return candidates[0]

        # 2. Inspect structured JSON output
        if isinstance(data, dict):
            for key in ["output", "output_path", "output_file", "project", "project_path", "file", "path", "export_path"]:
                val = data.get(key)
                if isinstance(val, str):
                    p = Path(val)
                    if p.is_file() or (p.suffix.lower() in PRIORITY_PROJECT_EXTENSIONS and p.parent.exists()):
                        return p

        # 3. Inspect command-line arguments for output paths
        if args:
            for i, arg in enumerate(args):
                if arg in ("-o", "--output", "--out", "-f", "--file") and i + 1 < len(args):
                    p = Path(args[i + 1])
                    if p.is_file() or (p.suffix.lower() in PRIORITY_PROJECT_EXTENSIONS and p.parent.exists()):
                        return p
                # Direct file path arguments
                p = Path(arg)
                if p.suffix.lower() in PRIORITY_PROJECT_EXTENSIONS:
                    if p.is_file() or p.parent.exists():
                        return p

        return None

    def visualize(
        self,
        harness: str,
        artifacts_created: List[str],
        data: Optional[Any] = None,
        args: Optional[List[str]] = None,
        wait_for_settle: bool = True,
        settle_timeout_sec: float = 3.5,
        play_chime: bool = True,
    ) -> Dict[str, Any]:
        """
        Brings the result of a CLI harness execution onto the user's physical display.
        1. Resolves target artifact
        2. Launches or activates the desktop application
        3. Waits for visual stabilization via SOUL-Gateman
        4. Triggers acoustic chime and ambient border pulse
        """
        ensure_dpi_aware()
        attach_input_desktop()
        t0 = time.perf_counter()

        target_file = self.find_target_artifact(artifacts_created, data=data, args=args)
        clean_slug = harness.replace("cli-anything-", "").replace("cli_anything-", "").strip().lower()

        method = "none"
        window_title: Optional[str] = None
        window_hwnd: Optional[int] = None
        app_target: Optional[str] = None
        opened_path: Optional[str] = str(target_file.resolve()) if target_file else None

        try:
            # Check if there is an installed desktop application matching the harness
            desktop_exe = resolve_executable(clean_slug)

            if target_file and target_file.is_file():
                if desktop_exe:
                    logger.info("[Visualizer] Launching %s with artifact: %s", clean_slug, target_file)
                    l_res = launch_app(app_name=clean_slug, args=[str(target_file)], wait_for_window=True, timeout=5.0)
                    method = "launch_app"
                    app_target = l_res.target_executed
                    if l_res.matched_hwnd:
                        window_hwnd = l_res.matched_hwnd
                        window_title = l_res.matched_title
                else:
                    logger.info("[Visualizer] Opening artifact via OS association: %s", target_file)
                    ok = open_uri(str(target_file))
                    method = "open_uri" if ok else "failed_open"
            elif desktop_exe:
                # No file created, but app is installed: activate or launch the app
                logger.info("[Visualizer] Focusing/launching app %s", clean_slug)
                l_res = launch_app(app_name=clean_slug, wait_for_window=True, timeout=3.0)
                method = "launch_app"
                app_target = l_res.target_executed
                if l_res.matched_hwnd:
                    window_hwnd = l_res.matched_hwnd
                    window_title = l_res.matched_title

            # Window foreground focus check
            if not window_hwnd:
                fg = get_foreground_window()
                if fg:
                    window_hwnd = fg.hwnd
                    window_title = fg.title

            # Force activate if window is known
            if window_hwnd:
                try:
                    force_activate_window(window_hwnd)
                except Exception:
                    pass

            # Visual settle detection via SOUL-Gateman
            settle_res = {"settled": True, "duration_ms": 0.0}
            if wait_for_settle:
                try:
                    from extra.core.soul.gateman import _default_gateman
                    settle_res = _default_gateman.wait_until_settled(timeout_sec=settle_timeout_sec)
                except Exception as ex:
                    logger.debug("[Visualizer] Settle detection skipped: %s", ex)

            # Ambient indicators: flash emerald green edge pulse & play acoustic chime
            if play_chime:
                try:
                    from extra.core.indicators import get_indicator_controller
                    ctrl = get_indicator_controller()
                    ctrl.task_complete(
                        summary=f"Rendered {clean_slug.title()}: {target_file.name if target_file else 'Complete'}",
                        success=True,
                        play_chime=True,
                    )
                except Exception as ex:
                    logger.debug("[Visualizer] Indicator chime skipped: %s", ex)

            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            return {
                "visualized": True,
                "artifact_path": opened_path,
                "method": method,
                "app_target": app_target,
                "window_title": window_title,
                "window_hwnd": window_hwnd,
                "settle_ms": settle_res.get("duration_ms", 0.0),
                "settled": settle_res.get("settled", True),
                "duration_ms": elapsed_ms,
            }

        except Exception as ex:
            logger.warning("[Visualizer] Visualization error: %s", ex)
            return {
                "visualized": False,
                "artifact_path": opened_path,
                "method": "error",
                "error": str(ex),
                "duration_ms": (time.perf_counter() - t0) * 1000.0,
            }


# Global singleton visualizer
_default_visualizer = DualPlaneVisualizer()


def visualize_harness_outcome(
    harness: str,
    artifacts_created: List[str],
    data: Optional[Any] = None,
    args: Optional[List[str]] = None,
    wait_for_settle: bool = True,
    settle_timeout_sec: float = 3.5,
    play_chime: bool = True,
) -> Dict[str, Any]:
    """Helper to visualize a completed harness execution."""
    return _default_visualizer.visualize(
        harness=harness,
        artifacts_created=artifacts_created,
        data=data,
        args=args,
        wait_for_settle=wait_for_settle,
        settle_timeout_sec=settle_timeout_sec,
        play_chime=play_chime,
    )
