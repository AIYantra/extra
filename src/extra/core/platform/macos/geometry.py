"""
Project Extra — macOS Geometry & Retina Coordinate Normalization Engine
Converts logical points, physical Retina pixels, and normalized [0, 1000] coordinates
with inverted Y-axis compensation for Apple macOS displays.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple, Union

from extra.core.platform.base import (
    AbstractGeometry,
    MonitorInfo,
    get_bbox_center,
)

logger = logging.getLogger("extra.geometry.macos")

try:
    import Quartz.CoreGraphics as CG
    from AppKit import NSScreen, NSEvent
except ImportError:
    CG = None
    NSScreen = None
    NSEvent = None


def ensure_dpi_aware() -> bool:
    """macOS handles Retina DPI scaling natively at the Cocoa/Quartz layer."""
    return True


def attach_input_desktop() -> bool:
    """macOS does not isolate desktop sessions via Win32 desktop station objects."""
    return True


def get_monitors_info() -> List[MonitorInfo]:
    """
    Discovers all active macOS displays, querying physical bounds,
    logical point dimensions, and Retina backing scale factors.
    """
    if CG is None:
        # Fallback dummy display if pyobjc is not present (e.g. non-macOS test runner)
        return [
            MonitorInfo(
                index=0,
                left=0,
                top=0,
                right=1920,
                bottom=1080,
                width=1920,
                height=1080,
                is_primary=True,
                device_name="Default macOS Display",
                dpi_x=144,
                dpi_y=144,
                scale_factor=2.0,
            )
        ]

    monitors: List[MonitorInfo] = []
    main_display_id = CG.CGMainDisplayID()
    _, displays, count = CG.CGGetActiveDisplayList(16, None, None)

    screens = NSScreen.screens() if NSScreen is not None else None

    for idx, display_id in enumerate(displays[:count]):
        rect = CG.CGDisplayBounds(display_id)
        is_primary = (display_id == main_display_id)

        scale_factor = 2.0
        if screens and idx < len(screens):
            try:
                scale_factor = float(screens[idx].backingScaleFactor())
            except Exception:
                scale_factor = 2.0

        # CGDisplayBounds returns coordinates in logical points with primary display top-left as (0, 0)
        pt_left = int(rect.origin.x)
        pt_top = int(rect.origin.y)
        pt_w = int(rect.size.width)
        pt_h = int(rect.size.height)

        # Compute physical hardware pixels
        phys_left = int(round(pt_left * scale_factor))
        phys_top = int(round(pt_top * scale_factor))
        phys_w = int(round(pt_w * scale_factor))
        phys_h = int(round(pt_h * scale_factor))

        monitors.append(
            MonitorInfo(
                index=idx,
                left=phys_left,
                top=phys_top,
                right=phys_left + phys_w,
                bottom=phys_top + phys_h,
                width=phys_w,
                height=phys_h,
                is_primary=is_primary,
                device_name=f"Display-{display_id}",
                dpi_x=int(72 * scale_factor),
                dpi_y=int(72 * scale_factor),
                scale_factor=scale_factor,
            )
        )

    # Primary monitor is always index 0
    monitors.sort(key=lambda m: (not m.is_primary, m.left, m.top))
    return [
        MonitorInfo(
            index=i,
            left=m.left,
            top=m.top,
            right=m.right,
            bottom=m.bottom,
            width=m.width,
            height=m.height,
            is_primary=m.is_primary,
            device_name=m.device_name,
            dpi_x=m.dpi_x,
            dpi_y=m.dpi_y,
            scale_factor=m.scale_factor,
        )
        for i, m in enumerate(monitors)
    ]


def get_primary_monitor() -> MonitorInfo:
    """Returns the primary display's information."""
    monitors = get_monitors_info()
    for m in monitors:
        if m.is_primary:
            return m
    return monitors[0]


def get_virtual_screen_bounds() -> Tuple[int, int, int, int]:
    """Returns the union bounding rectangle encompassing all displays (left, top, width, height)."""
    monitors = get_monitors_info()
    min_x = min(m.left for m in monitors)
    min_y = min(m.top for m in monitors)
    max_x = max(m.right for m in monitors)
    max_y = max(m.bottom for m in monitors)
    return (min_x, min_y, max_x - min_x, max_y - min_y)


def points_to_pixels(pt_x: Union[int, float], pt_y: Union[int, float], monitor_index: int = 0) -> Tuple[int, int]:
    """Converts macOS logical point coordinates to physical Retina pixels."""
    monitors = get_monitors_info()
    mon = monitors[monitor_index] if 0 <= monitor_index < len(monitors) else get_primary_monitor()
    scale = mon.scale_factor
    return (int(round(pt_x * scale)), int(round(pt_y * scale)))


def pixels_to_points(px_x: int, px_y: int, monitor_index: int = 0) -> Tuple[float, float]:
    """Converts physical Retina pixels to macOS logical points."""
    monitors = get_monitors_info()
    mon = monitors[monitor_index] if 0 <= monitor_index < len(monitors) else get_primary_monitor()
    scale = max(1.0, mon.scale_factor)
    return (px_x / scale, px_y / scale)


def flip_y_quartz_to_topleft(quartz_y: Union[int, float], monitor_height_pts: Union[int, float]) -> float:
    """Inverts bottom-left origin Quartz Y coordinate to top-left origin Y."""
    return float(monitor_height_pts - quartz_y)


def flip_y_topleft_to_quartz(topleft_y: Union[int, float], monitor_height_pts: Union[int, float]) -> float:
    """Inverts top-left origin Y coordinate to bottom-left origin Quartz Y."""
    return float(monitor_height_pts - topleft_y)


def get_cursor_position(as_points: bool = False) -> Tuple[int, int]:
    """
    Returns the current mouse cursor coordinates with top-left origin.
    By default, returns physical Retina pixels. Set as_points=True for logical points.
    """
    if CG is None:
        return (0, 0)

    event = CG.CGEventCreate(None)
    if not event:
        return (0, 0)

    # CGEventGetLocation returns logical points in top-left screen coordinate system
    loc = CG.CGEventGetLocation(event)
    pt_x, pt_y = float(loc.x), float(loc.y)

    if as_points:
        return (int(round(pt_x)), int(round(pt_y)))

    # Convert to physical pixels
    mon = get_primary_monitor()
    scale = mon.scale_factor
    return (int(round(pt_x * scale)), int(round(pt_y * scale)))


def normalize_coordinates(
    phys_x: int, phys_y: int, monitor_index: int = 0
) -> Tuple[int, int]:
    """
    Converts physical hardware screen pixel coordinates into normalized [0, 1000] scale.
    Standardized for multimodal vision models (Sonnet, GPT-4o, Astra 6).
    """
    monitors = get_monitors_info()
    target_mon = monitors[monitor_index] if 0 <= monitor_index < len(monitors) else get_primary_monitor()

    rel_x = phys_x - target_mon.left
    rel_y = phys_y - target_mon.top

    norm_x = int(round((rel_x / max(1, target_mon.width)) * 1000))
    norm_y = int(round((rel_y / max(1, target_mon.height)) * 1000))

    return (max(0, min(1000, norm_x)), max(0, min(1000, norm_y)))


def denormalize_coordinates(
    norm_x: Union[int, float],
    norm_y: Union[int, float],
    monitor_index: int = 0,
    as_points: bool = False,
) -> Tuple[int, int]:
    """
    Converts normalized [0, 1000] (or [0.0, 1.0]) coordinates back to exact physical pixels
    (or logical points when as_points=True for CoreGraphics event generation).
    """
    monitors = get_monitors_info()
    target_mon = monitors[monitor_index] if 0 <= monitor_index < len(monitors) else get_primary_monitor()

    scale = 1000.0 if (norm_x > 1.0 or norm_y > 1.0) else 1.0
    factor_x = float(norm_x) / scale
    factor_y = float(norm_y) / scale

    phys_x = int(round(target_mon.left + (factor_x * target_mon.width)))
    phys_y = int(round(target_mon.top + (factor_y * target_mon.height)))

    clamped_x, clamped_y = clamp_coordinates(phys_x, phys_y, monitor_index)

    if as_points:
        pt_x, pt_y = pixels_to_points(clamped_x, clamped_y, monitor_index)
        return (int(round(pt_x)), int(round(pt_y)))

    return (clamped_x, clamped_y)


def normalize_bbox(
    rect: Tuple[int, int, int, int], monitor_index: int = 0
) -> Tuple[int, int, int, int]:
    """Converts physical bounding box (left, top, right, bottom) to normalized [0, 1000] box."""
    left, top, right, bottom = rect
    x1, y1 = normalize_coordinates(left, top, monitor_index)
    x2, y2 = normalize_coordinates(right, bottom, monitor_index)
    return (x1, y1, x2, y2)


def denormalize_bbox(
    bbox: Tuple[Union[int, float], Union[int, float], Union[int, float], Union[int, float]],
    monitor_index: int = 0,
    as_points: bool = False,
) -> Tuple[int, int, int, int]:
    """Converts normalized bounding box back to physical pixel bounding box (or points)."""
    x1, y1, x2, y2 = bbox
    left, top = denormalize_coordinates(x1, y1, monitor_index, as_points=as_points)
    right, bottom = denormalize_coordinates(x2, y2, monitor_index, as_points=as_points)
    return (left, top, right, bottom)


def clamp_coordinates(
    phys_x: int, phys_y: int, monitor_index: int = 0
) -> Tuple[int, int]:
    """Clamps coordinates to ensure they reside strictly within monitor bounds."""
    monitors = get_monitors_info()
    target_mon = monitors[monitor_index] if 0 <= monitor_index < len(monitors) else get_primary_monitor()

    clamped_x = max(target_mon.left, min(target_mon.right - 1, phys_x))
    clamped_y = max(target_mon.top, min(target_mon.bottom - 1, phys_y))
    return (clamped_x, clamped_y)


class MacGeometry(AbstractGeometry):
    """macOS implementation of the AbstractGeometry interface."""

    def ensure_dpi_aware(self) -> bool:
        return ensure_dpi_aware()

    def attach_input_desktop(self) -> bool:
        return attach_input_desktop()

    def get_monitors_info(self) -> List[MonitorInfo]:
        return get_monitors_info()

    def get_primary_monitor(self) -> MonitorInfo:
        return get_primary_monitor()

    def get_virtual_screen_bounds(self) -> Tuple[int, int, int, int]:
        return get_virtual_screen_bounds()

    def get_cursor_position(self) -> Tuple[int, int]:
        return get_cursor_position()

    def normalize_coordinates(
        self, phys_x: int, phys_y: int, monitor_index: int = 0
    ) -> Tuple[int, int]:
        return normalize_coordinates(phys_x, phys_y, monitor_index)

    def denormalize_coordinates(
        self, norm_x: Union[int, float], norm_y: Union[int, float], monitor_index: int = 0
    ) -> Tuple[int, int]:
        return denormalize_coordinates(norm_x, norm_y, monitor_index)

    def normalize_bbox(
        self, rect: Tuple[int, int, int, int], monitor_index: int = 0
    ) -> Tuple[int, int, int, int]:
        return normalize_bbox(rect, monitor_index)

    def denormalize_bbox(
        self,
        bbox: Tuple[Union[int, float], Union[int, float], Union[int, float], Union[int, float]],
        monitor_index: int = 0,
    ) -> Tuple[int, int, int, int]:
        return denormalize_bbox(bbox, monitor_index)

    def clamp_coordinates(
        self, phys_x: int, phys_y: int, monitor_index: int = 0
    ) -> Tuple[int, int]:
        return clamp_coordinates(phys_x, phys_y, monitor_index)
