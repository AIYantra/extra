"""
Project Extra — Linux Geometry & Multi-Monitor Normalization Engine
Handles physical screen coordinates, display scaling (devicePixelRatio),
and normalized [0, 1000] bounding-box mathematics across Wayland and X11.
"""

from __future__ import annotations

import ctypes
import logging
import os
import re
import shutil
import subprocess
import sys
from typing import List, Optional, Tuple, Union

from extra.core.platform.base import (
    AbstractGeometry,
    MonitorInfo,
    get_bbox_center,
)

logger = logging.getLogger("extra.geometry.linux")

_cached_monitors: Optional[List[MonitorInfo]] = None
_software_cursor_pos: Tuple[int, int] = (0, 0)


def ensure_dpi_aware() -> bool:
    """Linux Wayland and X11 manage DPI scaling via compositor or Xft/XRandR."""
    return True


def attach_input_desktop() -> bool:
    """Linux uses standard UNIX sockets and sessions; no Win32 desktop station attach needed."""
    return True


def _discover_screens_via_qt() -> Optional[List[MonitorInfo]]:
    """Attempts to discover monitors using PySide6 QtGui QGuiApplication."""
    try:
        from PySide6.QtGui import QGuiApplication
        app = QGuiApplication.instance()
        if app is None:
            # Avoid creating GUI loop if not running; headless QGuiApplication is lightweight
            app = QGuiApplication(sys.argv[:1])

        screens = QGuiApplication.screens()
        if not screens:
            return None

        monitors: List[MonitorInfo] = []
        for idx, s in enumerate(screens):
            geo = s.geometry()
            dpr = float(s.devicePixelRatio())
            # Physical pixel bounds
            left = int(geo.x() * dpr)
            top = int(geo.y() * dpr)
            width = int(geo.width() * dpr)
            height = int(geo.height() * dpr)
            right = left + width
            bottom = top + height
            is_primary = (s == QGuiApplication.primaryScreen())

            dpi = int(s.logicalDotsPerInch() * dpr) if hasattr(s, "logicalDotsPerInch") else 96

            monitors.append(
                MonitorInfo(
                    index=idx,
                    left=left,
                    top=top,
                    right=right,
                    bottom=bottom,
                    width=width,
                    height=height,
                    is_primary=is_primary,
                    device_name=s.name() or f"Display-{idx}",
                    dpi_x=dpi,
                    dpi_y=dpi,
                    scale_factor=dpr,
                )
            )
        return monitors
    except Exception as e:
        logger.debug(f"Qt screen discovery unavailable: {e}")
        return None


def _discover_screens_via_xrandr() -> Optional[List[MonitorInfo]]:
    """Fallback display discovery using xrandr CLI."""
    if not shutil.which("xrandr"):
        return None

    try:
        output = subprocess.check_output(["xrandr", "--current"], text=True, timeout=1.0)
        monitors: List[MonitorInfo] = []
        idx = 0
        # eDP-1 connected primary 1366x768+0+0 (normal...)
        pattern = re.compile(r"^(\S+) connected (primary )?(\d+)x(\d+)\+(\d+)\+(\d+)")
        for line in output.splitlines():
            match = pattern.match(line)
            if match:
                dev_name, primary_flag, w_str, h_str, x_str, y_str = match.groups()
                w, h = int(w_str), int(h_str)
                x, y = int(x_str), int(y_str)
                is_prim = bool(primary_flag) or (idx == 0)

                monitors.append(
                    MonitorInfo(
                        index=idx,
                        left=x,
                        top=y,
                        right=x + w,
                        bottom=y + h,
                        width=w,
                        height=h,
                        is_primary=is_prim,
                        device_name=dev_name,
                        dpi_x=96,
                        dpi_y=96,
                        scale_factor=1.0,
                    )
                )
                idx += 1
        return monitors if monitors else None
    except Exception as e:
        logger.debug(f"xrandr discovery error: {e}")
        return None


def get_monitors_info(force_refresh: bool = False) -> List[MonitorInfo]:
    """
    Discovers all physical displays and their hardware bounds.
    Tiers:
    1. PySide6 QGuiApplication screens (handles Wayland fractional scaling & multi-monitor)
    2. xrandr command output (X11 & XWayland)
    3. Default primary display fallback (1920x1080)
    """
    global _cached_monitors
    if _cached_monitors and not force_refresh:
        return _cached_monitors

    screens = _discover_screens_via_qt()
    if not screens:
        screens = _discover_screens_via_xrandr()

    if not screens:
        screens = [
            MonitorInfo(
                index=0,
                left=0,
                top=0,
                right=1920,
                bottom=1080,
                width=1920,
                height=1080,
                is_primary=True,
                device_name="Default Linux Display",
                dpi_x=96,
                dpi_y=96,
                scale_factor=1.0,
            )
        ]

    _cached_monitors = screens
    return screens


def get_primary_monitor() -> MonitorInfo:
    """Returns the designated primary display."""
    monitors = get_monitors_info()
    for m in monitors:
        if m.is_primary:
            return m
    return monitors[0]


def get_virtual_screen_bounds() -> Tuple[int, int, int, int]:
    """
    Returns virtual desktop bounding box across all connected monitors:
    (min_left, min_top, total_width, total_height)
    """
    monitors = get_monitors_info()
    min_x = min(m.left for m in monitors)
    min_y = min(m.top for m in monitors)
    max_r = max(m.right for m in monitors)
    max_b = max(m.bottom for m in monitors)
    return (min_x, min_y, max_r - min_x, max_b - min_y)


def get_cursor_position() -> Tuple[int, int]:
    """
    Retrieves current mouse cursor physical coordinates (x, y).
    1. Uses xdotool getmouselocation --shell (fast & crash-proof across X11 & XWayland).
    2. Uses PySide6 QCursor.pos() if GUI application is active.
    3. Falls back to internal tracked synthetic cursor position.
    """
    global _software_cursor_pos

    # 1. Try xdotool
    if shutil.which("xdotool"):
        try:
            out = subprocess.check_output(
                ["xdotool", "getmouselocation", "--shell"], text=True, timeout=0.2
            )
            data = {}
            for line in out.splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    data[k.strip().upper()] = v.strip()
            if "X" in data and "Y" in data:
                return (int(data["X"]), int(data["Y"]))
        except Exception:
            pass

    # 2. Try PySide6 QCursor
    try:
        from PySide6.QtGui import QCursor
        pos = QCursor.pos()
        if pos is not None:
            return (int(pos.x()), int(pos.y()))
    except Exception:
        pass

    return _software_cursor_pos


def set_tracked_cursor_position(x: int, y: int) -> None:
    """Updates the internal synthetic cursor tracking coordinates."""
    global _software_cursor_pos
    _software_cursor_pos = (x, y)


def normalize_coordinates(
    phys_x: int, phys_y: int, monitor_index: int = 0
) -> Tuple[int, int]:
    """
    Maps physical display coordinates (pixels) into normalized [0, 1000] scale.
    """
    monitors = get_monitors_info()
    mon = monitors[monitor_index] if 0 <= monitor_index < len(monitors) else monitors[0]

    rel_x = phys_x - mon.left
    rel_y = phys_y - mon.top

    norm_x = int(round((rel_x / max(1, mon.width)) * 1000))
    norm_y = int(round((rel_y / max(1, mon.height)) * 1000))

    return (max(0, min(1000, norm_x)), max(0, min(1000, norm_y)))


def denormalize_coordinates(
    norm_x: Union[int, float], norm_y: Union[int, float], monitor_index: int = 0
) -> Tuple[int, int]:
    """
    Converts normalized [0, 1000] coordinates back into exact physical display pixels.
    """
    monitors = get_monitors_info()
    mon = monitors[monitor_index] if 0 <= monitor_index < len(monitors) else monitors[0]

    norm_x_clamped = max(0.0, min(1000.0, float(norm_x)))
    norm_y_clamped = max(0.0, min(1000.0, float(norm_y)))

    phys_x = mon.left + int(round((norm_x_clamped / 1000.0) * mon.width))
    phys_y = mon.top + int(round((norm_y_clamped / 1000.0) * mon.height))

    return clamp_coordinates(phys_x, phys_y, monitor_index)


def normalize_bbox(
    rect: Tuple[int, int, int, int], monitor_index: int = 0
) -> Tuple[int, int, int, int]:
    """Normalizes physical pixel rectangle (left, top, right, bottom) to [0, 1000]."""
    x1, y1 = normalize_coordinates(rect[0], rect[1], monitor_index)
    x2, y2 = normalize_coordinates(rect[2], rect[3], monitor_index)
    return (x1, y1, x2, y2)


def denormalize_bbox(
    bbox: Tuple[Union[int, float], Union[int, float], Union[int, float], Union[int, float]],
    monitor_index: int = 0,
) -> Tuple[int, int, int, int]:
    """Denormalizes [0, 1000] bounding box to physical screen pixel coordinates."""
    x1, y1 = denormalize_coordinates(bbox[0], bbox[1], monitor_index)
    x2, y2 = denormalize_coordinates(bbox[2], bbox[3], monitor_index)
    return (x1, y1, x2, y2)


def clamp_coordinates(
    phys_x: int, phys_y: int, monitor_index: int = 0
) -> Tuple[int, int]:
    """Clamps physical coordinates to stay within target display boundaries."""
    monitors = get_monitors_info()
    mon = monitors[monitor_index] if 0 <= monitor_index < len(monitors) else monitors[0]

    clamped_x = max(mon.left, min(mon.right - 1, phys_x))
    clamped_y = max(mon.top, min(mon.bottom - 1, phys_y))
    return (clamped_x, clamped_y)


class LinuxGeometry(AbstractGeometry):
    """Concrete implementation of AbstractGeometry for Linux."""

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
        return normalize_coordinates(phys_x, phys_y, monitor_index=monitor_index)

    def denormalize_coordinates(
        self, norm_x: Union[int, float], norm_y: Union[int, float], monitor_index: int = 0
    ) -> Tuple[int, int]:
        return denormalize_coordinates(norm_x, norm_y, monitor_index=monitor_index)

    def normalize_bbox(
        self, rect: Tuple[int, int, int, int], monitor_index: int = 0
    ) -> Tuple[int, int, int, int]:
        return normalize_bbox(rect, monitor_index=monitor_index)

    def denormalize_bbox(
        self,
        bbox: Tuple[Union[int, float], Union[int, float], Union[int, float], Union[int, float]],
        monitor_index: int = 0,
    ) -> Tuple[int, int, int, int]:
        return denormalize_bbox(bbox, monitor_index=monitor_index)

    def clamp_coordinates(
        self, phys_x: int, phys_y: int, monitor_index: int = 0
    ) -> Tuple[int, int]:
        return clamp_coordinates(phys_x, phys_y, monitor_index=monitor_index)


PlatformGeometry = LinuxGeometry
