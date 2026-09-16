"""
Project Extra — macOS CoreGraphics Hardware-Level Input Engine
Sub-millisecond mouse dispatch, instant UTF-16 Unicode typing, and atomic clipboard swaps.
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional, Tuple, Union

from extra.core.platform.base import AbstractInputEngine
from extra.core.platform.macos.geometry import (
    clamp_coordinates,
    get_cursor_position,
    pixels_to_points,
    points_to_pixels,
)

logger = logging.getLogger("extra.input.macos")

try:
    import Quartz.CoreGraphics as CG
    from AppKit import NSPasteboard, NSPasteboardTypeString
except ImportError:
    CG = None
    NSPasteboard = None
    NSPasteboardTypeString = None

# macOS Virtual Keycodes (Carbon / HIToolbox)
MAC_KEY_MAP: Dict[str, int] = {
    # System Control Keys
    "return": 36, "enter": 36, "tab": 48, "space": 49, "backspace": 51,
    "delete": 117, "del": 117, "escape": 53, "esc": 53,
    "command": 55, "cmd": 55, "lcmd": 55, "rcmd": 54,
    "shift": 56, "capslock": 57, "option": 58, "alt": 58,
    "control": 59, "ctrl": 59, "right_shift": 60, "right_option": 61,
    "right_control": 62, "fn": 63,
    # Navigation
    "left": 123, "right": 124, "down": 125, "up": 126,
    "home": 115, "end": 119, "pageup": 116, "pagedown": 121, "help": 114,
    # Function Keys
    "f1": 122, "f2": 120, "f3": 99, "f4": 118, "f5": 96, "f6": 97,
    "f7": 98, "f8": 100, "f9": 101, "f10": 109, "f11": 103, "f12": 111,
    # Standard QWERTY Alphanumeric Mappings
    "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7, "c": 8, "v": 9,
    "b": 11, "q": 12, "w": 13, "e": 14, "r": 15, "y": 16, "t": 17, "1": 18, "2": 19,
    "3": 20, "4": 21, "6": 22, "5": 23, "equal": 24, "9": 25, "7": 26, "minus": 27,
    "8": 28, "0": 29, "rightbracket": 30, "o": 31, "u": 32, "leftbracket": 33, "i": 34,
    "p": 35, "l": 37, "j": 38, "quote": 39, "k": 40, "semicolon": 41, "backslash": 42,
    "comma": 43, "slash": 44, "n": 45, "m": 46, "period": 47,
}

# Maximum characters allowed per CGEventKeyboardSetUnicodeString call
MAX_UNICODE_CHUNK = 20


def _notify_indicator(
    action: str,
    x: Optional[int] = None,
    y: Optional[int] = None,
    monitor_index: int = 0,
) -> None:
    """Helper to dispatch real-time feedback to indicator controller without latency."""
    try:
        from extra.core.platform.macos.indicators import get_indicator_controller
        get_indicator_controller().task_action(
            action_type=action, x=x or 0, y=y or 0, monitor_index=monitor_index
        )
    except Exception:
        pass


def instant_type(text: str, press_enter: bool = False) -> None:
    """
    Injects Unicode text directly into the system HID event tap on macOS in sub-3ms.
    Bypasses keyboard layouts, scancode conversions, and macOS IME input switching.
    Supports complex scripts, foreign alphabets, and emojis (UTF-16 surrogate pairs).
    """
    if not text and not press_enter:
        return

    if CG is None:
        logger.warning("CoreGraphics unavailable; instant_type skipped.")
        return

    # Ingest text in safe UTF-16 chunks
    if text:
        for i in range(0, len(text), MAX_UNICODE_CHUNK):
            chunk = text[i : i + MAX_UNICODE_CHUNK]
            event = CG.CGEventCreateKeyboardEvent(None, 0, True)
            CG.CGEventKeyboardSetUnicodeString(event, len(chunk), chunk)
            CG.CGEventPost(CG.kCGHIDEventTap, event)

    if press_enter:
        # Keycode 36 = kVK_Return
        kd = CG.CGEventCreateKeyboardEvent(None, 36, True)
        ku = CG.CGEventCreateKeyboardEvent(None, 36, False)
        CG.CGEventPost(CG.kCGHIDEventTap, kd)
        CG.CGEventPost(CG.kCGHIDEventTap, ku)

    _notify_indicator("type")


def atomic_clipboard_paste(text: str, restore_delay: float = 0.02) -> None:
    """
    Safely injects massive text blocks or multi-line code snippets via NSPasteboard:
    1. Saves existing pasteboard items & types.
    2. Writes target text with NSPasteboardTypeString.
    3. Triggers hardware Command+V.
    4. Restores original pasteboard contents within 20ms.
    """
    if NSPasteboard is None:
        instant_type(text)
        return

    pb = NSPasteboard.generalPasteboard()
    old_types = list(pb.types() or [])
    old_data: Dict[str, Any] = {}

    try:
        for t in old_types:
            d = pb.dataForType_(t)
            if d is not None:
                old_data[t] = d

        pb.clearContents()
        pb.setString_forType_(text, NSPasteboardTypeString)
    except Exception as ex:
        logger.debug("Failed setting NSPasteboard, falling back to instant_type: %s", ex)
        instant_type(text)
        return

    # Dispatch Command + V keystroke
    send_hotkey(["cmd", "v"])
    time.sleep(restore_delay)

    # Restore previous pasteboard contents
    if old_data:
        try:
            pb.clearContents()
            for t, d in old_data.items():
                pb.setData_forType_(d, t)
        except Exception:
            pass


def mouse_move(x: int, y: int, monitor_index: int = 0, notify: bool = True) -> None:
    """Positions the mouse cursor at exact screen coordinates via CoreGraphics."""
    if CG is None:
        return

    cx, cy = clamp_coordinates(x, y, monitor_index)
    pt_x, pt_y = pixels_to_points(cx, cy, monitor_index)

    event = CG.CGEventCreateMouseEvent(
        None, CG.kCGEventMouseMoved, (pt_x, pt_y), CG.kCGMouseButtonLeft
    )
    CG.CGEventPost(CG.kCGHIDEventTap, event)

    if notify:
        _notify_indicator("move", cx, cy, monitor_index)


def mouse_down(button: str = "left") -> None:
    """Depresses a mouse button."""
    if CG is None:
        return

    pt_x, pt_y = get_cursor_position(as_points=True)
    b = button.lower().strip()
    if b == "right":
        event_type = CG.kCGEventRightMouseDown
        mouse_btn = CG.kCGMouseButtonRight
    elif b == "middle":
        event_type = CG.kCGEventOtherMouseDown
        mouse_btn = CG.kCGMouseButtonCenter
    else:
        event_type = CG.kCGEventLeftMouseDown
        mouse_btn = CG.kCGMouseButtonLeft

    event = CG.CGEventCreateMouseEvent(None, event_type, (pt_x, pt_y), mouse_btn)
    CG.CGEventPost(CG.kCGHIDEventTap, event)


def mouse_up(button: str = "left") -> None:
    """Releases a mouse button."""
    if CG is None:
        return

    pt_x, pt_y = get_cursor_position(as_points=True)
    b = button.lower().strip()
    if b == "right":
        event_type = CG.kCGEventRightMouseUp
        mouse_btn = CG.kCGMouseButtonRight
    elif b == "middle":
        event_type = CG.kCGEventOtherMouseUp
        mouse_btn = CG.kCGMouseButtonCenter
    else:
        event_type = CG.kCGEventLeftMouseUp
        mouse_btn = CG.kCGMouseButtonLeft

    event = CG.CGEventCreateMouseEvent(None, event_type, (pt_x, pt_y), mouse_btn)
    CG.CGEventPost(CG.kCGHIDEventTap, event)


def mouse_click(
    x: Optional[int] = None,
    y: Optional[int] = None,
    button: str = "left",
    clicks: int = 1,
    interval: float = 0.05,
    monitor_index: int = 0,
) -> None:
    """
    Executes hardware-level mouse click(s) at target coordinates.
    Utilizes macOS kCGMouseEventClickState (1, 2, 3) for native double/triple clicks.
    """
    if x is not None and y is not None:
        mouse_move(x, y, monitor_index, notify=False)
        time.sleep(0.01)

    pt_x, pt_y = get_cursor_position(as_points=True)
    _notify_indicator("click", x, y, monitor_index)

    if CG is None:
        return

    b = button.lower().strip()
    if b == "right":
        down_type = CG.kCGEventRightMouseDown
        up_type = CG.kCGEventRightMouseUp
        mouse_btn = CG.kCGMouseButtonRight
    elif b == "middle":
        down_type = CG.kCGEventOtherMouseDown
        up_type = CG.kCGEventOtherMouseUp
        mouse_btn = CG.kCGMouseButtonCenter
    else:
        down_type = CG.kCGEventLeftMouseDown
        up_type = CG.kCGEventLeftMouseUp
        mouse_btn = CG.kCGMouseButtonLeft

    for i in range(1, clicks + 1):
        down_evt = CG.CGEventCreateMouseEvent(None, down_type, (pt_x, pt_y), mouse_btn)
        CG.CGEventSetIntegerValueField(down_evt, CG.kCGMouseEventClickState, i)
        CG.CGEventPost(CG.kCGHIDEventTap, down_evt)

        up_evt = CG.CGEventCreateMouseEvent(None, up_type, (pt_x, pt_y), mouse_btn)
        CG.CGEventSetIntegerValueField(up_evt, CG.kCGMouseEventClickState, i)
        CG.CGEventPost(CG.kCGHIDEventTap, up_evt)

        if i < clicks:
            time.sleep(interval)


def mouse_double_click(x: Optional[int] = None, y: Optional[int] = None, monitor_index: int = 0) -> None:
    """Executes a native double left click with clickState: 2."""
    mouse_click(x, y, button="left", clicks=2, interval=0.06, monitor_index=monitor_index)


def mouse_drag(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    button: str = "left",
    steps: int = 15,
    duration: float = 0.2,
    monitor_index: int = 0,
) -> None:
    """Performs smooth hardware click-and-drag from start to end coordinates."""
    mouse_move(start_x, start_y, monitor_index, notify=False)
    time.sleep(0.02)
    mouse_down(button)
    time.sleep(0.02)

    step_delay = duration / max(1, steps)
    start_pt_x, start_pt_y = pixels_to_points(start_x, start_y, monitor_index)
    end_pt_x, end_pt_y = pixels_to_points(end_x, end_y, monitor_index)

    if CG is not None:
        drag_type = CG.kCGEventRightMouseDragged if button.lower() == "right" else CG.kCGEventLeftMouseDragged
        mouse_btn = CG.kCGMouseButtonRight if button.lower() == "right" else CG.kCGMouseButtonLeft

        for s in range(1, steps + 1):
            ratio = s / float(steps)
            cur_pt_x = start_pt_x + (end_pt_x - start_pt_x) * ratio
            cur_pt_y = start_pt_y + (end_pt_y - start_pt_y) * ratio
            drag_evt = CG.CGEventCreateMouseEvent(None, drag_type, (cur_pt_x, cur_pt_y), mouse_btn)
            CG.CGEventPost(CG.kCGHIDEventTap, drag_evt)
            time.sleep(step_delay)

    time.sleep(0.02)
    mouse_up(button)
    _notify_indicator("drag", end_x, end_y, monitor_index)


def mouse_scroll(delta: int, horizontal: bool = False) -> None:
    """
    Scrolls the mouse wheel vertically or horizontally.
    Positive delta scrolls up/right, negative scrolls down/left.
    """
    if CG is None:
        return

    # kCGScrollEventUnitLine (0)
    event = CG.CGEventCreateScrollWheelEvent(
        None, 0, 1 if not horizontal else 2, delta
    )
    CG.CGEventPost(CG.kCGHIDEventTap, event)
    _notify_indicator("scroll")


def send_hotkey(keys: List[str]) -> None:
    """
    Dispatches a synchronized hotkey sequence using macOS virtual keycodes.
    Presses all keys sequentially, then releases them in reverse order.
    """
    if not keys or CG is None:
        return

    vk_codes: List[int] = []
    for k in keys:
        clean = k.lower().strip()
        if clean in MAC_KEY_MAP:
            vk_codes.append(MAC_KEY_MAP[clean])
        elif len(clean) == 1 and clean.isalpha():
            vk_codes.append(MAC_KEY_MAP.get(clean, 0))

    # Press down in order
    for vk in vk_codes:
        event = CG.CGEventCreateKeyboardEvent(None, vk, True)
        CG.CGEventPost(CG.kCGHIDEventTap, event)
    time.sleep(0.02)

    # Release up in reverse order
    for vk in reversed(vk_codes):
        event = CG.CGEventCreateKeyboardEvent(None, vk, False)
        CG.CGEventPost(CG.kCGHIDEventTap, event)

    _notify_indicator("hotkey")


class MacInputEngine(AbstractInputEngine):
    """macOS implementation of the AbstractInputEngine interface."""

    def mouse_move(self, x: int, y: int, monitor_index: int = 0) -> None:
        mouse_move(x, y, monitor_index)

    def mouse_down(self, button: str = "left") -> None:
        mouse_down(button)

    def mouse_up(self, button: str = "left") -> None:
        mouse_up(button)

    def mouse_click(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: str = "left",
        clicks: int = 1,
        interval: float = 0.05,
        monitor_index: int = 0,
    ) -> None:
        mouse_click(x, y, button, clicks, interval, monitor_index)

    def mouse_double_click(
        self, x: Optional[int] = None, y: Optional[int] = None, monitor_index: int = 0
    ) -> None:
        mouse_double_click(x, y, monitor_index)

    def mouse_drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        button: str = "left",
        steps: int = 15,
        duration: float = 0.2,
        monitor_index: int = 0,
    ) -> None:
        mouse_drag(start_x, start_y, end_x, end_y, button, steps, duration, monitor_index)

    def mouse_scroll(self, delta: int, horizontal: bool = False) -> None:
        mouse_scroll(delta, horizontal)

    def instant_type(self, text: str, press_enter: bool = False) -> None:
        instant_type(text, press_enter)

    def send_hotkey(self, keys: List[str]) -> None:
        send_hotkey(keys)

    def atomic_clipboard_paste(self, text: str) -> None:
        atomic_clipboard_paste(text)
