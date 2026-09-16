"""
Project Extra — Win32 Native Platform Backend
"""

from extra.core.platform.windows.capture import (
    ScreenCaptureEngine,
    capture_roi,
    capture_screen,
    get_capture_engine,
)
from extra.core.platform.windows.focus import (
    WindowInfo,
    WindowsFocusManager,
    find_window_by_title,
    find_windows_by_process,
    force_activate_window,
    get_foreground_window,
    get_window_info,
    list_windows,
)
from extra.core.platform.windows.geometry import (
    MonitorInfo,
    WindowsGeometry,
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
from extra.core.platform.windows.indicators import (
    AudioIndicator,
    IndicatorController,
    get_indicator_controller,
)
from extra.core.platform.windows.input_engine import (
    WindowsInputEngine,
    atomic_clipboard_paste,
    instant_type,
    mouse_click,
    mouse_double_click,
    mouse_down,
    mouse_drag,
    mouse_move,
    mouse_scroll,
    mouse_up,
    send_hotkey,
)
from extra.core.platform.windows.shell import (
    APP_REGISTRY,
    BROWSER_CANDIDATE_PATHS,
    LaunchResult,
    WindowsShellLauncher,
    launch_app,
    open_uri,
    resolve_executable,
)
from extra.core.platform.windows.uia_plane import (
    SetOfMarkAnnotator,
    UIAutomationPlane,
    UIElement,
)

__all__ = [
    # Geometry
    "ensure_dpi_aware",
    "attach_input_desktop",
    "get_monitors_info",
    "get_primary_monitor",
    "get_virtual_screen_bounds",
    "normalize_coordinates",
    "denormalize_coordinates",
    "normalize_bbox",
    "denormalize_bbox",
    "get_bbox_center",
    "clamp_coordinates",
    "get_cursor_position",
    "MonitorInfo",
    "WindowsGeometry",
    # Capture
    "ScreenCaptureEngine",
    "get_capture_engine",
    "capture_screen",
    "capture_roi",
    # Input
    "instant_type",
    "atomic_clipboard_paste",
    "mouse_move",
    "mouse_down",
    "mouse_up",
    "mouse_click",
    "mouse_double_click",
    "mouse_drag",
    "mouse_scroll",
    "send_hotkey",
    "WindowsInputEngine",
    # Focus
    "WindowInfo",
    "get_window_info",
    "get_foreground_window",
    "list_windows",
    "find_window_by_title",
    "find_windows_by_process",
    "force_activate_window",
    "WindowsFocusManager",
    # UIA Plane
    "UIAutomationPlane",
    "SetOfMarkAnnotator",
    "UIElement",
    # Task Indicators
    "AudioIndicator",
    "IndicatorController",
    "get_indicator_controller",
    # Shell Launcher
    "launch_app",
    "open_uri",
    "resolve_executable",
    "APP_REGISTRY",
    "BROWSER_CANDIDATE_PATHS",
    "LaunchResult",
    "WindowsShellLauncher",
]
