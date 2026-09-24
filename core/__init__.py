"""
Project Extra — Core Engine Package
High-performance Windows 10/11 desktop automation, dual-plane perception,
zero-latency SendInput injection, and closed-loop stall breaker.
"""

from extra.core.capture import (
    CaptureResult,
    ScreenCaptureEngine,
    capture_roi,
    capture_screen,
    get_capture_engine,
    image_to_base64,
)
from extra.core.focus import (
    WindowInfo,
    find_window_by_title,
    find_windows_by_process,
    force_activate_window,
    get_foreground_window,
    get_window_info,
    list_windows,
)
from extra.core.geometry import (
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
from extra.core.indicators import (
    AudioIndicator,
    IndicatorController,
    get_indicator_controller,
)
from extra.core.input_engine import (
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
from extra.core.stall_breaker import (
    ActionOutcome,
    EmergencyAbortError,
    StallBreaker,
    StallStatus,
)
from extra.core.uia_plane import (
    SetOfMarkAnnotator,
    UIAutomationPlane,
    UIElement,
)
from extra.core.soul import (
    DecisionType,
    SoulDecision,
    SoulDecider,
    get_soul_decider,
    get_soul_runtime,
    SoulEyes,
    get_soul_eyes,
    visual_ground,
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
    # Capture
    "ScreenCaptureEngine",
    "get_capture_engine",
    "capture_screen",
    "capture_roi",
    "image_to_base64",
    "CaptureResult",
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
    # Focus
    "WindowInfo",
    "get_window_info",
    "get_foreground_window",
    "list_windows",
    "find_window_by_title",
    "find_windows_by_process",
    "force_activate_window",
    # UIA Plane
    "UIAutomationPlane",
    "SetOfMarkAnnotator",
    "UIElement",
    # Stall Breaker
    "StallBreaker",
    "StallStatus",
    "ActionOutcome",
    "EmergencyAbortError",
    # Task Indicators
    "AudioIndicator",
    "IndicatorController",
    "get_indicator_controller",
    # Project SOUL (System One Ultra-fast Layer)
    "SoulDecider",
    "SoulDecision",
    "DecisionType",
    "get_soul_decider",
    "get_soul_runtime",
    "SoulEyes",
    "get_soul_eyes",
    "visual_ground",
]
