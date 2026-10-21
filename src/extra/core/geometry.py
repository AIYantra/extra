"""
Project Extra — Geometry & Coordinate Mapping Engine (PAL Facade)
Re-exports geometry functions and classes from the active platform backend.
"""

from __future__ import annotations

from extra.core.platform import (
    MonitorInfo,
    attach_input_desktop,
    clamp_coordinates,
    denormalize_bbox,
    denormalize_coordinates,
    ensure_dpi_aware,
    get_bbox_center,
    get_cursor_position,
    get_monitors_info,
    get_primary_monitor,
    get_virtual_screen_bounds,
    normalize_bbox,
    normalize_coordinates,
)

__all__ = [
    "MonitorInfo",
    "attach_input_desktop",
    "clamp_coordinates",
    "denormalize_bbox",
    "denormalize_coordinates",
    "ensure_dpi_aware",
    "get_bbox_center",
    "get_cursor_position",
    "get_monitors_info",
    "get_primary_monitor",
    "get_virtual_screen_bounds",
    "normalize_bbox",
    "normalize_coordinates",
]
