"""
Project Extra — Geometry & Multi-Monitor DPI Normalization Engine
Hardware-level physical pixel coordinates, PerMonitorV2 awareness,
and normalized [0, 1000] bounding-box mathematics for Windows 10/11.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

# Win32 DPI Awareness Context Constants
DPI_AWARENESS_CONTEXT_UNAWARE = ctypes.c_void_p(-1)
DPI_AWARENESS_CONTEXT_SYSTEM_AWARE = ctypes.c_void_p(-2)
DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE = ctypes.c_void_p(-3)
DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.c_void_p(-4)

# Monitor Metrics Constants
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79
MONITORINFOF_PRIMARY = 0x00000001
MDT_EFFECTIVE_DPI = 0

# Desktop Security Access Mask
DESKTOP_ALL = 0x01FF

user32 = ctypes.windll.user32
shcore = getattr(ctypes.windll, "shcore", None)
kernel32 = ctypes.windll.kernel32


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32),
    ]


class POINT(ctypes.Structure):
    _fields_ = [
        ("x", wintypes.LONG),
        ("y", wintypes.LONG),
    ]


# Monitor enumeration callback type
MONITORENUMPROC = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.HMONITOR,
    wintypes.HDC,
    ctypes.POINTER(RECT),
    wintypes.LPARAM,
)


@dataclass(frozen=True)
class MonitorInfo:
    """Represents physical display hardware metrics and DPI scaling."""
    index: int
    left: int
    top: int
    right: int
    bottom: int
    width: int
    height: int
    is_primary: bool
    device_name: str
    dpi_x: int
    dpi_y: int
    scale_factor: float


_dpi_initialized = False


def ensure_dpi_aware() -> bool:
    """
    Enforces Windows 10/11 PerMonitorV2 DPI awareness for the current process.
    Guarantees all Win32 coordinate queries and mouse inputs target exact
    physical display hardware pixels without virtualization distortion.
    """
    global _dpi_initialized
    if _dpi_initialized:
        return True

    # 1. Try Windows 10 (1703+) PerMonitorAwareV2 via user32
    if hasattr(user32, "SetProcessDpiAwarenessContext"):
        user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        user32.SetProcessDpiAwarenessContext.restype = wintypes.BOOL
        try:
            if user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2):
                _dpi_initialized = True
                return True
        except Exception:
            pass

    # 2. Try Windows 8.1+ PROCESS_PER_MONITOR_DPI_AWARE (2) via shcore
    if shcore and hasattr(shcore, "SetProcessDpiAwareness"):
        shcore.SetProcessDpiAwareness.argtypes = [ctypes.c_int]
        shcore.SetProcessDpiAwareness.restype = wintypes.HRESULT
        try:
            res = shcore.SetProcessDpiAwareness(2)
            if res == 0:  # S_OK
                _dpi_initialized = True
                return True
        except Exception:
            pass

    # 3. Fallback to legacy Vista/7 SetProcessDPIAware via user32
    if hasattr(user32, "SetProcessDPIAware"):
        user32.SetProcessDPIAware.restype = wintypes.BOOL
        try:
            if user32.SetProcessDPIAware():
                _dpi_initialized = True
                return True
        except Exception:
            pass

    _dpi_initialized = True
    return False


def attach_input_desktop() -> bool:
    """
    Attaches the current calling thread to the active interactive input desktop.
    Required for background agents, subshells, and automation services on Windows.
    """
    try:
        user32.OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        user32.OpenInputDesktop.restype = wintypes.HANDLE
        user32.SetThreadDesktop.argtypes = [wintypes.HANDLE]
        user32.SetThreadDesktop.restype = wintypes.BOOL

        hDesk = user32.OpenInputDesktop(0, False, DESKTOP_ALL)
        if hDesk:
            res = user32.SetThreadDesktop(hDesk)
            return bool(res)
    except Exception:
        pass
    return False


def get_monitors_info() -> List[MonitorInfo]:
    """
    Discovers all physical and virtual monitors with their bounding coordinates,
    primary status, and exact DPI scaling factors.
    """
    ensure_dpi_aware()
    monitors: List[MonitorInfo] = []

    def _enum_proc(hMonitor: int, hdc: int, lprcMonitor: Any, dwData: int) -> int:
        info = MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(MONITORINFOEXW)
        if user32.GetMonitorInfoW(hMonitor, ctypes.byref(info)):
            left = int(info.rcMonitor.left)
            top = int(info.rcMonitor.top)
            right = int(info.rcMonitor.right)
            bottom = int(info.rcMonitor.bottom)
            width = right - left
            height = bottom - top
            is_primary = bool(info.dwFlags & MONITORINFOF_PRIMARY)
            device_name = str(info.szDevice)

            # Query per-monitor DPI if supported
            dpi_x = 96
            dpi_y = 96
            if shcore and hasattr(shcore, "GetDpiForMonitor"):
                try:
                    dpi_x_val = wintypes.UINT()
                    dpi_y_val = wintypes.UINT()
                    shcore.GetDpiForMonitor.argtypes = [
                        wintypes.HMONITOR,
                        ctypes.c_int,
                        ctypes.POINTER(wintypes.UINT),
                        ctypes.POINTER(wintypes.UINT),
                    ]
                    shcore.GetDpiForMonitor.restype = wintypes.HRESULT
                    if shcore.GetDpiForMonitor(hMonitor, MDT_EFFECTIVE_DPI, ctypes.byref(dpi_x_val), ctypes.byref(dpi_y_val)) == 0:
                        dpi_x = int(dpi_x_val.value)
                        dpi_y = int(dpi_y_val.value)
                except Exception:
                    pass

            scale_factor = round(dpi_x / 96.0, 2)
            monitors.append(
                MonitorInfo(
                    index=len(monitors),
                    left=left,
                    top=top,
                    right=right,
                    bottom=bottom,
                    width=width,
                    height=height,
                    is_primary=is_primary,
                    device_name=device_name,
                    dpi_x=dpi_x,
                    dpi_y=dpi_y,
                    scale_factor=scale_factor,
                )
            )
        return 1

    proc = MONITORENUMPROC(_enum_proc)
    user32.EnumDisplayMonitors(None, None, proc, 0)

    # Sort so that primary monitor is always index 0
    monitors.sort(key=lambda m: (not m.is_primary, m.left, m.top))
    # Re-index
    return [
        MonitorInfo(
            index=idx,
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
        for idx, m in enumerate(monitors)
    ]


def get_virtual_screen_bounds() -> Tuple[int, int, int, int]:
    """
    Returns the bounding rectangle encompassing all connected monitors:
    (left, top, width, height).
    """
    ensure_dpi_aware()
    left = int(user32.GetSystemMetrics(SM_XVIRTUALSCREEN))
    top = int(user32.GetSystemMetrics(SM_YVIRTUALSCREEN))
    width = int(user32.GetSystemMetrics(SM_CXVIRTUALSCREEN))
    height = int(user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))
    return (left, top, width, height)


def get_primary_monitor() -> MonitorInfo:
    """Returns the primary monitor's information."""
    monitors = get_monitors_info()
    for m in monitors:
        if m.is_primary:
            return m
    if monitors:
        return monitors[0]
    # Fallback to virtual screen if no monitors enumerated
    vx, vy, vw, vh = get_virtual_screen_bounds()
    return MonitorInfo(
        index=0,
        left=vx,
        top=vy,
        right=vx + vw,
        bottom=vy + vh,
        width=vw,
        height=vh,
        is_primary=True,
        device_name="Default",
        dpi_x=96,
        dpi_y=96,
        scale_factor=1.0,
    )


def normalize_coordinates(
    phys_x: int, phys_y: int, monitor_index: int = 0
) -> Tuple[int, int]:
    """
    Converts physical hardware screen pixel coordinates into normalized [0, 1000] scale.
    Standardized for vision models (Sonnet, GPT-4o, Astra 6).
    """
    monitors = get_monitors_info()
    target_mon = monitors[monitor_index] if 0 <= monitor_index < len(monitors) else get_primary_monitor()

    rel_x = phys_x - target_mon.left
    rel_y = phys_y - target_mon.top

    norm_x = int(round((rel_x / max(1, target_mon.width)) * 1000))
    norm_y = int(round((rel_y / max(1, target_mon.height)) * 1000))

    return (max(0, min(1000, norm_x)), max(0, min(1000, norm_y)))


def denormalize_coordinates(
    norm_x: int | float, norm_y: int | float, monitor_index: int = 0
) -> Tuple[int, int]:
    """
    Converts model-predicted normalized [0, 1000] (or [0.0, 1.0]) coordinates
    back to exact physical display pixels.
    """
    monitors = get_monitors_info()
    target_mon = monitors[monitor_index] if 0 <= monitor_index < len(monitors) else get_primary_monitor()

    # Support both [0.0, 1.0] and [0, 1000] scales
    scale = 1000.0 if (norm_x > 1.0 or norm_y > 1.0) else 1.0

    factor_x = float(norm_x) / scale
    factor_y = float(norm_y) / scale

    phys_x = int(round(target_mon.left + (factor_x * target_mon.width)))
    phys_y = int(round(target_mon.top + (factor_y * target_mon.height)))

    return clamp_coordinates(phys_x, phys_y, monitor_index)


def normalize_bbox(
    rect: Tuple[int, int, int, int], monitor_index: int = 0
) -> Tuple[int, int, int, int]:
    """
    Converts physical pixel bounding box (left, top, right, bottom)
    to normalized [0, 1000] bounding box (x1, y1, x2, y2).
    """
    left, top, right, bottom = rect
    x1, y1 = normalize_coordinates(left, top, monitor_index)
    x2, y2 = normalize_coordinates(right, bottom, monitor_index)
    return (x1, y1, x2, y2)


def denormalize_bbox(
    bbox: Tuple[int | float, int | float, int | float, int | float],
    monitor_index: int = 0,
) -> Tuple[int, int, int, int]:
    """
    Converts normalized bounding box (x1, y1, x2, y2)
    back to physical pixel bounding box (left, top, right, bottom).
    """
    x1, y1, x2, y2 = bbox
    left, top = denormalize_coordinates(x1, y1, monitor_index)
    right, bottom = denormalize_coordinates(x2, y2, monitor_index)
    return (left, top, right, bottom)


def get_bbox_center(bbox: Tuple[int, int, int, int]) -> Tuple[int, int]:
    """Computes the geometric center point (x, y) of a bounding box."""
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) // 2, (y1 + y2) // 2)


def clamp_coordinates(
    phys_x: int, phys_y: int, monitor_index: int = 0
) -> Tuple[int, int]:
    """Clamps physical coordinates to ensure they reside strictly within monitor bounds."""
    monitors = get_monitors_info()
    target_mon = monitors[monitor_index] if 0 <= monitor_index < len(monitors) else get_primary_monitor()

    clamped_x = max(target_mon.left, min(target_mon.right - 1, phys_x))
    clamped_y = max(target_mon.top, min(target_mon.bottom - 1, phys_y))
    return (clamped_x, clamped_y)


def get_cursor_position() -> Tuple[int, int]:
    """Returns the current mouse cursor physical coordinates (x, y)."""
    ensure_dpi_aware()
    attach_input_desktop()
    pt = POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return (int(pt.x), int(pt.y))


# Automatically initialize DPI awareness and attach input desktop on module import
ensure_dpi_aware()
attach_input_desktop()
