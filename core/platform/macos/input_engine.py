"""
Project Extra — macOS CoreGraphics Hardware-Level Input Engine
Sub-millisecond mouse dispatch, instant UTF-16 Unicode typing, and atomic clipboard swaps.
"""

from __future__ import annotations

import logging
import math
import random
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from extra.core.motion import (
    apply_jitter,
    generate_bezier_path,
    generate_stroke_path,
    generate_windmouse_path,
    FittsProfiler,
)
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


def smooth_mouse_move(
    x: int,
    y: int,
    speed: str = "normal",
    style: str = "bezier",
    monitor_index: int = 0,
    overshoot: bool = True,
    notify: bool = True,
) -> None:
    """
    Glides the mouse cursor to screen coordinates (x, y) along a human-like biomechanical trajectory on macOS.
    """
    if CG is None:
        return

    target_x, target_y = clamp_coordinates(x, y, monitor_index)
    start_x, start_y = get_cursor_position(as_points=False)
    distance = math.hypot(target_x - start_x, target_y - start_y)

    if distance < 3.0:
        mouse_move(target_x, target_y, monitor_index=monitor_index, notify=notify)
        return

    if style.lower() == "windmouse":
        speed_factor = 1.0 if speed == "normal" else (0.55 if speed == "fast" else 1.8)
        scheduled_steps = generate_windmouse_path(
            (start_x, start_y),
            (target_x, target_y),
            gravity=9.0,
            wind=3.0,
            min_wait=0.002 * speed_factor,
            max_wait=0.008 * speed_factor,
            max_step=16.0 if speed == "fast" else (10.0 if speed == "normal" else 6.0),
        )
    else:  # "bezier"
        duration = FittsProfiler.calculate_duration(distance, speed=speed)
        ox_pt = FittsProfiler.generate_overshoot((start_x, start_y), (target_x, target_y), distance) if overshoot else None
        if ox_pt:
            steps1 = max(10, int(distance / 25))
            path1 = generate_bezier_path((start_x, start_y), ox_pt, steps=steps1, deviation_factor=0.20)
            path2 = generate_bezier_path(ox_pt, (target_x, target_y), steps=5, deviation_factor=0.10)
            full_path = path1 + path2[1:]
        else:
            steps_count = max(12, min(50, int(distance / 18)))
            full_path = generate_bezier_path((start_x, start_y), (target_x, target_y), steps=steps_count)

        full_path = apply_jitter(full_path, amplitude=1.0, frequency=0.35)
        scheduled_steps = FittsProfiler.schedule_path(full_path, total_duration=duration)

    for px, py, delay in scheduled_steps:
        cx, cy = clamp_coordinates(px, py, monitor_index)
        pt_x, pt_y = pixels_to_points(cx, cy, monitor_index)
        event = CG.CGEventCreateMouseEvent(None, CG.kCGEventMouseMoved, (pt_x, pt_y), CG.kCGMouseButtonLeft)
        CG.CGEventPost(CG.kCGHIDEventTap, event)
        time.sleep(delay)

    mouse_move(target_x, target_y, monitor_index=monitor_index, notify=notify)


def mouse_stroke(
    points: List[Tuple[int, int]],
    button: str = "left",
    duration: float = 1.0,
    smooth: bool = True,
    monitor_index: int = 0,
) -> None:
    """
    Executes a continuous smooth brush stroke across multiple waypoints while holding button on macOS.
    """
    if not points or CG is None:
        return

    clamped_pts = [clamp_coordinates(p[0], p[1], monitor_index) for p in points]
    if len(clamped_pts) == 1:
        mouse_click(clamped_pts[0][0], clamped_pts[0][1], button=button, monitor_index=monitor_index)
        return

    start_x, start_y = clamped_pts[0]
    mouse_move(start_x, start_y, monitor_index=monitor_index, notify=False)
    time.sleep(0.02)

    mouse_down(button)
    time.sleep(0.02)

    drag_type = CG.kCGEventRightMouseDragged if button.lower() == "right" else CG.kCGEventLeftMouseDragged
    mouse_btn = CG.kCGMouseButtonRight if button.lower() == "right" else CG.kCGMouseButtonLeft

    scheduled = generate_stroke_path(clamped_pts, duration=duration, smooth=smooth)
    for px, py, delay in scheduled:
        cx, cy = clamp_coordinates(px, py, monitor_index)
        pt_x, pt_y = pixels_to_points(cx, cy, monitor_index)
        drag_evt = CG.CGEventCreateMouseEvent(None, drag_type, (pt_x, pt_y), mouse_btn)
        CG.CGEventPost(CG.kCGHIDEventTap, drag_evt)
        time.sleep(delay)

    time.sleep(0.02)
    mouse_up(button)
    last_x, last_y = clamped_pts[-1]
    _notify_indicator("drag", last_x, last_y, monitor_index)


def mouse_click(
    x: Optional[int] = None,
    y: Optional[int] = None,
    button: str = "left",
    clicks: int = 1,
    interval: float = 0.05,
    monitor_index: int = 0,
    human_like: bool = False,
    speed: str = "normal",
) -> None:
    """
    Executes hardware-level mouse click(s) at target coordinates.
    Utilizes macOS kCGMouseEventClickState (1, 2, 3) for native double/triple clicks.
    If human_like=True, glides to target via Bézier trajectory with natural reaction delay.
    """
    if x is not None and y is not None:
        if human_like:
            smooth_mouse_move(x, y, speed=speed, monitor_index=monitor_index, notify=False)
            time.sleep(random.uniform(0.03, 0.07))
        else:
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
    human_like: bool = False,
    style: str = "bezier",
) -> None:
    """Performs smooth hardware click-and-drag from start to end coordinates."""
    if human_like:
        mouse_stroke(
            [(start_x, start_y), (end_x, end_y)],
            button=button,
            duration=duration,
            smooth=False,
            monitor_index=monitor_index,
        )
        return

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

    def smooth_mouse_move(
        self,
        x: int,
        y: int,
        speed: str = "normal",
        style: str = "bezier",
        monitor_index: int = 0,
        overshoot: bool = True,
    ) -> None:
        smooth_mouse_move(
            x=x,
            y=y,
            speed=speed,
            style=style,
            monitor_index=monitor_index,
            overshoot=overshoot,
        )

    def mouse_stroke(
        self,
        points: List[Tuple[int, int]],
        button: str = "left",
        duration: float = 1.0,
        smooth: bool = True,
        monitor_index: int = 0,
    ) -> None:
        mouse_stroke(
            points=points,
            button=button,
            duration=duration,
            smooth=smooth,
            monitor_index=monitor_index,
        )

    def mouse_scroll(self, delta: int, horizontal: bool = False) -> None:
        mouse_scroll(delta, horizontal)

    def instant_type(self, text: str, press_enter: bool = False) -> None:
        instant_type(text, press_enter)

    def send_hotkey(self, keys: List[str]) -> None:
        send_hotkey(keys)

    def atomic_clipboard_paste(self, text: str) -> None:
        atomic_clipboard_paste(text)

    def execute_batch_actions(
        self, actions: List[Dict[str, Any]], auto_settle: bool = True
    ) -> Dict[str, Any]:
        return execute_batch_actions(actions=actions, auto_settle=auto_settle)


def execute_batch_actions(
    actions: List[Dict[str, Any]], auto_settle: bool = True, max_depth: int = 5
) -> Dict[str, Any]:
    """
    Executes an atomic list of hardware actions sequentially on macOS.
    Eliminates multi-turn LLM network round-trips for compound workflows.
    Enhanced with SOUL (System One Ultra-fast Layer) for dynamic branching ('eval', 'assert', 'wait_for_state').
    """
    t0 = time.perf_counter()
    executed: List[Dict[str, Any]] = []
    batch_error: Dict[str, Any] = {}

    def _get_active_context(explicit_ctx: Optional[Union[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
        ctx: Dict[str, Any] = {}
        if isinstance(explicit_ctx, dict):
            ctx.update(explicit_ctx)
        elif isinstance(explicit_ctx, str):
            ctx["text"] = explicit_ctx

        if "window_title" not in ctx:
            try:
                from extra.core.focus import get_foreground_window
                fg = get_foreground_window()
                if fg:
                    ctx["window_title"] = fg.title
                    ctx["process_name"] = fg.process_name
            except Exception:
                pass
        return ctx

    def _execute_sub_list(action_list: List[Dict[str, Any]], depth: int = 0) -> bool:
        if depth > max_depth:
            return True

        for act in action_list:
            atype = str(act.get("action", act.get("type", ""))).lower().strip()
            if not atype:
                continue

            step_t0 = time.perf_counter()
            current_index = len(executed)

            # ── SOUL Reflexive Actions ─────────────────────────────────────
            if atype in ("eval", "condition", "branch"):
                condition = str(act.get("condition", act.get("query", "")))
                if_true = act.get("if_true", act.get("then", []))
                if_false = act.get("if_false", act.get("else", []))
                explicit_ctx = act.get("context")

                from extra.core.soul import get_soul_decider
                decider = get_soul_decider()
                ctx = _get_active_context(explicit_ctx)

                eval_t0 = time.perf_counter()
                decision = decider.decide_boolean(condition, context=ctx)
                eval_dur = (time.perf_counter() - eval_t0) * 1000.0

                branch_name = "if_true" if decision.result else "if_false"
                branch_actions = if_true if decision.result else if_false

                executed.append({
                    "index": current_index,
                    "action": "eval",
                    "condition": condition,
                    "result": decision.result,
                    "confidence": decision.confidence,
                    "branch": branch_name,
                    "sub_actions_count": len(branch_actions) if isinstance(branch_actions, list) else 0,
                    "duration_ms": round(eval_dur, 2),
                })

                if isinstance(branch_actions, list) and branch_actions:
                    ok = _execute_sub_list(branch_actions, depth=depth + 1)
                    if not ok:
                        return False

            elif atype in ("assert", "check"):
                condition = str(act.get("condition", act.get("query", "")))
                on_fail = str(act.get("on_fail", "abort")).lower()
                max_retries = int(act.get("max_retries", 2))
                retry_actions = act.get("retry_actions", [])
                explicit_ctx = act.get("context")

                from extra.core.soul import get_soul_decider
                decider = get_soul_decider()

                passed = False
                for attempt in range(max_retries + 1):
                    ctx = _get_active_context(explicit_ctx)
                    decision = decider.decide_boolean(condition, context=ctx)
                    if decision.result:
                        passed = True
                        break
                    if attempt < max_retries and isinstance(retry_actions, list) and retry_actions:
                        _execute_sub_list(retry_actions, depth=depth + 1)

                step_dur = (time.perf_counter() - step_t0) * 1000.0
                executed.append({
                    "index": current_index,
                    "action": "assert",
                    "condition": condition,
                    "passed": passed,
                    "on_fail": on_fail,
                    "duration_ms": round(step_dur, 2),
                })

                if not passed:
                    if on_fail == "abort":
                        batch_error["error"] = f"Assertion failed on condition: '{condition}'"
                        return False

            elif atype in ("wait_for_state", "wait_until", "poll_state"):
                condition = str(act.get("condition", act.get("query", "")))
                timeout_ms = int(act.get("timeout_ms", 2000))
                poll_interval_ms = int(act.get("poll_interval_ms", 50))
                target_state = bool(act.get("target_state", True))
                explicit_ctx = act.get("context")

                from extra.core.soul import get_soul_decider
                decider = get_soul_decider()

                t_start = time.perf_counter()
                satisfied = False
                while (time.perf_counter() - t_start) * 1000.0 < timeout_ms:
                    ctx = _get_active_context(explicit_ctx)
                    decision = decider.decide_boolean(condition, context=ctx)
                    if decision.result == target_state:
                        satisfied = True
                        break
                    time.sleep(poll_interval_ms / 1000.0)

                step_dur = (time.perf_counter() - step_t0) * 1000.0
                executed.append({
                    "index": current_index,
                    "action": "wait_for_state",
                    "condition": condition,
                    "satisfied": satisfied,
                    "duration_ms": round(step_dur, 2),
                })

            # ── Standard Hardware Actions ──────────────────────────────────
            elif atype in ("hotkey", "shortcut"):
                keys = act.get("keys", [])
                if isinstance(keys, str):
                    keys = [keys]
                send_hotkey(keys)
                step_dur = (time.perf_counter() - step_t0) * 1000.0
                executed.append({"index": current_index, "action": "hotkey", "keys": keys, "duration_ms": round(step_dur, 2)})

            elif atype in ("type", "text", "input"):
                text = str(act.get("text", ""))
                press_enter = bool(act.get("press_enter", False))
                instant_type(text, press_enter=press_enter)
                step_dur = (time.perf_counter() - step_t0) * 1000.0
                executed.append({"index": current_index, "action": "type", "length": len(text), "press_enter": press_enter, "duration_ms": round(step_dur, 2)})

            elif atype in ("move", "mouse_move", "hover"):
                x = act.get("x")
                y = act.get("y")
                human = bool(act.get("human_like", False))
                speed = str(act.get("speed", "normal"))
                style = str(act.get("style", "bezier"))
                if x is not None and y is not None:
                    if human:
                        smooth_mouse_move(int(x), int(y), speed=speed, style=style)
                    else:
                        mouse_move(int(x), int(y))
                step_dur = (time.perf_counter() - step_t0) * 1000.0
                executed.append({"index": current_index, "action": "move", "x": x, "y": y, "human_like": human, "duration_ms": round(step_dur, 2)})

            elif atype in ("stroke", "draw", "brush"):
                pts = act.get("points", [])
                btn = str(act.get("button", "left"))
                dur = float(act.get("duration", 1.0))
                sm = bool(act.get("smooth", True))
                pts_tuples = [(int(p[0]), int(p[1])) for p in pts if len(p) >= 2]
                if pts_tuples:
                    mouse_stroke(pts_tuples, button=btn, duration=dur, smooth=sm)
                step_dur = (time.perf_counter() - step_t0) * 1000.0
                executed.append({"index": current_index, "action": "stroke", "point_count": len(pts_tuples), "duration_ms": round(step_dur, 2)})

            elif atype in ("click", "mouse_click"):
                target = act.get("target", act.get("query"))
                if target and ("x" not in act and "y" not in act):
                    from extra.core.soul import visual_ground
                    ground_res = visual_ground(query=str(target))
                    if ground_res.matched and ground_res.screen_point:
                        x, y = ground_res.screen_point
                    else:
                        x, y = act.get("x"), act.get("y")
                else:
                    x = act.get("x")
                    y = act.get("y")

                btn = str(act.get("button", "left"))
                clicks = int(act.get("clicks", 1))
                human = bool(act.get("human_like", False))
                if human:
                    mouse_click(int(x) if x is not None else None, int(y) if y is not None else None, button=btn, clicks=clicks, human_like=human, speed=speed)
                else:
                    mouse_click(int(x) if x is not None else None, int(y) if y is not None else None, button=btn, clicks=clicks)
                step_dur = (time.perf_counter() - step_t0) * 1000.0
                exec_item = {"index": current_index, "action": "click", "x": x, "y": y, "button": btn, "human_like": human, "duration_ms": round(step_dur, 2)}
                if target:
                    exec_item["grounded_target"] = str(target)
                executed.append(exec_item)

            elif atype in ("double_click", "dblclick"):
                x = act.get("x")
                y = act.get("y")
                mouse_double_click(int(x) if x is not None else None, int(y) if y is not None else None)
                step_dur = (time.perf_counter() - step_t0) * 1000.0
                executed.append({"index": current_index, "action": "double_click", "x": x, "y": y, "duration_ms": round(step_dur, 2)})

            elif atype in ("focus", "activate"):
                title = act.get("window_title")
                hwnd = act.get("hwnd")
                from extra.core.platform.macos.focus import find_window_by_title, force_activate_window, get_foreground_window
                target_hwnd = int(hwnd) if hwnd else None
                success = False
                if not target_hwnd and title:
                    win = find_window_by_title(str(title), timeout=2.0)
                    if win:
                        target_hwnd = win.hwnd

                if target_hwnd:
                    success = force_activate_window(target_hwnd)

                # Tier 2 Closed-Loop Focus Verification
                verified_focus = False
                active_hwnd = None
                active_title = ""
                try:
                    fg = get_foreground_window()
                    if fg:
                        active_hwnd = fg.hwnd
                        active_title = fg.title
                        if target_hwnd and fg.hwnd == target_hwnd:
                            verified_focus = True
                        elif title and str(title).lower() in fg.title.lower():
                            verified_focus = True
                except Exception:
                    pass

                step_dur = (time.perf_counter() - step_t0) * 1000.0
                executed.append({
                    "index": current_index,
                    "action": "focus",
                    "target": title or hwnd,
                    "success": success and verified_focus,
                    "verified_focus": verified_focus,
                    "active_hwnd": active_hwnd,
                    "active_title": active_title,
                    "duration_ms": round(step_dur, 2),
                })

            elif atype in ("sleep", "wait", "pause"):
                if "seconds" in act:
                    ms = int(float(act["seconds"]) * 1000)
                else:
                    ms = int(act.get("ms", act.get("duration_ms", act.get("delay", act.get("delay_ms", act.get("duration", 100))))))
                time.sleep(ms / 1000.0)
                executed.append({"index": current_index, "action": "sleep", "ms": ms})

            elif atype in ("scroll", "wheel"):
                clicks = int(act.get("clicks", 1))
                direction = str(act.get("direction", "vertical"))
                mouse_scroll(delta=clicks * 120, horizontal=(direction.lower() == "horizontal"))
                step_dur = (time.perf_counter() - step_t0) * 1000.0
                executed.append({"index": current_index, "action": "scroll", "clicks": clicks, "direction": direction, "duration_ms": round(step_dur, 2)})

            # Tier 1 In-Memory Visual Settle / Physical Action Delay
            if "settle_ms" in act:
                time.sleep(int(act["settle_ms"]) / 1000.0)
            elif auto_settle and atype in ("click", "double_click", "focus", "activate", "hotkey", "scroll"):
                try:
                    from extra.core.soul.gateman import wait_until_settled
                    # Fast perceptual settle check (< 15ms if stable, up to 400ms if transitioning)
                    settle_res = wait_until_settled(timeout_sec=0.4, settle_frames=2, check_interval_ms=15)
                    if executed:
                        executed[-1]["settled"] = settle_res.get("settled", True)
                        executed[-1]["settle_ms"] = round(settle_res.get("duration_ms", 0.0), 2)
                except Exception:
                    time.sleep(0.02)
            else:
                default_settle = 0 if atype in ("eval", "condition", "branch", "assert", "check", "wait_for_state", "wait_until", "poll_state", "sleep", "wait", "pause") else 30
                if default_settle > 0:
                    time.sleep(default_settle / 1000.0)

        return True

    _execute_sub_list(actions, depth=0)

    total_ms = (time.perf_counter() - t0) * 1000.0
    result_dict: Dict[str, Any] = {
        "success": not bool(batch_error),
        "executed_count": len(executed),
        "total_duration_ms": round(total_ms, 2),
        "actions": executed,
    }
    if batch_error:
        result_dict.update(batch_error)
    return result_dict


