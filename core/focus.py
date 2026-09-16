"""
Project Extra — Window Focus & Foreground Enforcer (PAL Facade)
Re-exports window management functions and classes from the active platform backend.
"""

from __future__ import annotations

from extra.core.platform import (
    WindowInfo,
    find_window_by_title,
    find_windows_by_process,
    force_activate_window,
    get_foreground_window,
    get_window_info,
    list_windows,
)

__all__ = [
    "WindowInfo",
    "find_window_by_title",
    "find_windows_by_process",
    "force_activate_window",
    "get_foreground_window",
    "get_window_info",
    "list_windows",
]
