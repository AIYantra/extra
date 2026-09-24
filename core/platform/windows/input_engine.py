"""
Project Extra — Win32 Hardware-Level Input Engine
Sub-millisecond SendInput execution with KEYEVENTF_UNICODE (VK_PACKET),
atomic clipboard swap, multi-button hardware mouse dispatch, and hotkeys.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import math
import random
import time
from typing import List, Optional, Tuple, Union

import win32clipboard
import win32con

from extra.core.motion import (
    apply_jitter,
    generate_bezier_path,
    generate_stroke_path,
    generate_windmouse_path,
    FittsProfiler,
)
from extra.core.platform.base import AbstractInputEngine
from extra.core.platform.windows.geometry import (
    attach_input_desktop,
    clamp_coordinates,
    ensure_dpi_aware,
    get_cursor_position,
)

# Input Types
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

# Keyboard Flags
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

# Mouse Flags
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x1000
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000

# Virtual Key Mapping
VK_MAP = {
    "backspace": 0x08,
    "tab": 0x09,
    "clear": 0x0C,
    "enter": 0x0D,
    "return": 0x0D,
    "shift": 0x10,
    "ctrl": 0x11,
    "control": 0x11,
    "alt": 0x12,
    "pause": 0x13,
    "capslock": 0x14,
    "esc": 0x1B,
    "escape": 0x1B,
    "space": 0x20,
    "pageup": 0x21,
    "pagedown": 0x22,
    "end": 0x23,
    "home": 0x24,
    "left": 0x25,
    "up": 0x26,
    "right": 0x27,
    "down": 0x28,
    "select": 0x29,
    "print": 0x2A,
    "execute": 0x2B,
    "printscreen": 0x2C,
    "prtscr": 0x2C,
    "insert": 0x2D,
    "delete": 0x2E,
    "del": 0x2E,
    "help": 0x2F,
    "win": 0x5B,
    "windows": 0x5B,
    "lwin": 0x5B,
    "rwin": 0x5C,
    "apps": 0x5D,
    "sleep": 0x5F,
    "numpad0": 0x60,
    "numpad1": 0x61,
    "numpad2": 0x62,
    "numpad3": 0x63,
    "numpad4": 0x64,
    "numpad5": 0x65,
    "numpad6": 0x66,
    "numpad7": 0x67,
    "numpad8": 0x68,
    "numpad9": 0x69,
    "multiply": 0x6A,
    "add": 0x6B,
    "separator": 0x6C,
    "subtract": 0x6D,
    "decimal": 0x6E,
    "divide": 0x6F,
    "f1": 0x70,
    "f2": 0x71,
    "f3": 0x72,
    "f4": 0x73,
    "f5": 0x74,
    "f6": 0x75,
    "f7": 0x76,
    "f8": 0x77,
    "f9": 0x78,
    "f10": 0x79,
    "f11": 0x7A,
    "f12": 0x7B,
    "numlock": 0x90,
    "scrolllock": 0x91,
}

user32 = ctypes.windll.user32


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _anonymous_ = ("_u",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("_u", _INPUT_UNION),
    ]


LPINPUT = ctypes.POINTER(INPUT)
user32.SendInput.argtypes = [wintypes.UINT, LPINPUT, ctypes.c_int]
user32.SendInput.restype = wintypes.UINT
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.SetCursorPos.restype = wintypes.BOOL


def _notify_indicator(
    action: str,
    x: Optional[int] = None,
    y: Optional[int] = None,
    monitor_index: int = 0,
) -> None:
    """Helper to dispatch real-time feedback to indicator controller without latency."""
    try:
        from extra.core.platform.windows.indicators import get_indicator_controller
        get_indicator_controller().task_action(
            action=action, x=x, y=y, monitor_index=monitor_index
        )
    except Exception:
        pass


def _send_inputs(inputs: List[INPUT]) -> int:
    """Dispatches a batch of INPUT structs to the OS input pipeline."""
    if not inputs:
        return 0
    ensure_dpi_aware()
    attach_input_desktop()
    n = len(inputs)
    arr = (INPUT * n)(*inputs)
    return int(user32.SendInput(n, arr, ctypes.sizeof(INPUT)))


def instant_type(text: str, press_enter: bool = False) -> None:
    """
    Injects Unicode strings directly into the Windows input queue in sub-5ms.
    Uses Win32 KEYEVENTF_UNICODE with UTF-16 code units (supporting surrogate pairs for emojis).
    """
    if not text and not press_enter:
        return

    inputs: List[INPUT] = []

    # Encode to UTF-16-LE words to cleanly capture surrogate pairs (e.g., emojis)
    utf16_bytes = text.encode("utf-16-le")
    code_units = [
        int.from_bytes(utf16_bytes[i : i + 2], "little")
        for i in range(0, len(utf16_bytes), 2)
    ]

    for unit in code_units:
        # Key down
        kd = INPUT(type=INPUT_KEYBOARD)
        kd.ki = KEYBDINPUT(
            wVk=0,
            wScan=unit,
            dwFlags=KEYEVENTF_UNICODE,
            time=0,
            dwExtraInfo=0,
        )
        # Key up
        ku = INPUT(type=INPUT_KEYBOARD)
        ku.ki = KEYBDINPUT(
            wVk=0,
            wScan=unit,
            dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP,
            time=0,
            dwExtraInfo=0,
        )
        inputs.extend([kd, ku])

    if press_enter:
        kd_enter = INPUT(type=INPUT_KEYBOARD)
        kd_enter.ki = KEYBDINPUT(wVk=win32con.VK_RETURN, wScan=0, dwFlags=0, time=0, dwExtraInfo=0)
        ku_enter = INPUT(type=INPUT_KEYBOARD)
        ku_enter.ki = KEYBDINPUT(wVk=win32con.VK_RETURN, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)
        inputs.extend([kd_enter, ku_enter])

    _send_inputs(inputs)
    _notify_indicator("type")


def atomic_clipboard_paste(text: str, restore_delay: float = 0.02) -> None:
    """
    Safely injects massive text blocks or multi-line code snippets via clipboard:
    1. Saves current user clipboard content.
    2. Writes target text to clipboard.
    3. Triggers hardware Ctrl+V.
    4. Restores original clipboard content after restore_delay.
    """
    old_clipboard: Optional[str] = None
    try:
        win32clipboard.OpenClipboard()
        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
            old_clipboard = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
    except Exception:
        # Fallback to instant_type if clipboard lock is contended
        instant_type(text)
        return
    finally:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass

    # Send Ctrl+V
    send_hotkey(["ctrl", "v"])
    time.sleep(restore_delay)

    # Restore previous clipboard
    if old_clipboard is not None:
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, old_clipboard)
        except Exception:
            pass
        finally:
            try:
                win32clipboard.CloseClipboard()
            except Exception:
                pass


def mouse_move(x: int, y: int, monitor_index: int = 0, notify: bool = True) -> None:
    """Positions the mouse cursor at exact physical display coordinates."""
    ensure_dpi_aware()
    attach_input_desktop()
    cx, cy = clamp_coordinates(x, y, monitor_index)
    user32.SetCursorPos(cx, cy)
    
    # Also dispatch via SendInput for 100% reliable hardware positioning across all desktop sessions
    w = user32.GetSystemMetrics(0)
    h = user32.GetSystemMetrics(1)
    if w > 0 and h > 0:
        nx = int(cx * 65535 / (w - 1))
        ny = int(cy * 65535 / (h - 1))
        inp = INPUT(type=INPUT_MOUSE)
        inp.mi = MOUSEINPUT(
            dx=nx,
            dy=ny,
            mouseData=0,
            dwFlags=MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_MOVE | MOUSEEVENTF_VIRTUALDESK,
            time=0,
            dwExtraInfo=0,
        )
        _send_inputs([inp])

    if notify:
        _notify_indicator("move", cx, cy, monitor_index)


def mouse_down(button: str = "left") -> None:
    """Holds down the specified mouse button."""
    btn = button.lower()
    flag = MOUSEEVENTF_LEFTDOWN
    if btn == "right":
        flag = MOUSEEVENTF_RIGHTDOWN
    elif btn == "middle":
        flag = MOUSEEVENTF_MIDDLEDOWN

    inp = INPUT(type=INPUT_MOUSE)
    inp.mi = MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=flag, time=0, dwExtraInfo=0)
    _send_inputs([inp])


def mouse_up(button: str = "left") -> None:
    """Releases the specified mouse button."""
    btn = button.lower()
    flag = MOUSEEVENTF_LEFTUP
    if btn == "right":
        flag = MOUSEEVENTF_RIGHTUP
    elif btn == "middle":
        flag = MOUSEEVENTF_MIDDLEUP

    inp = INPUT(type=INPUT_MOUSE)
    inp.mi = MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=flag, time=0, dwExtraInfo=0)
    _send_inputs([inp])


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
    Glides the mouse cursor to physical coordinates (x, y) along a human-like biomechanical trajectory.
    Uses Bézier arcs or WindMouse physics, Fitts's Law Minimum Jerk velocity profiling,
    micro-jitter, and optional natural overshoot/correction.
    """
    ensure_dpi_aware()
    attach_input_desktop()
    target_x, target_y = clamp_coordinates(x, y, monitor_index)

    start_x, start_y = get_cursor_position()
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
        user32.SetCursorPos(cx, cy)
        time.sleep(delay)

    user32.SetCursorPos(target_x, target_y)
    if notify:
        _notify_indicator("move", target_x, target_y, monitor_index)


def mouse_stroke(
    points: List[Tuple[int, int]],
    button: str = "left",
    duration: float = 1.0,
    smooth: bool = True,
    monitor_index: int = 0,
) -> None:
    """
    Executes a continuous smooth brush stroke across multiple waypoints while holding button.
    Essential for Canva drawing, MS Paint sketching, and timeline scrubbing.
    """
    if not points:
        return

    ensure_dpi_aware()
    attach_input_desktop()

    clamped_pts = [clamp_coordinates(p[0], p[1], monitor_index) for p in points]
    if len(clamped_pts) == 1:
        mouse_click(clamped_pts[0][0], clamped_pts[0][1], button=button, monitor_index=monitor_index)
        return

    start_x, start_y = clamped_pts[0]
    mouse_move(start_x, start_y, monitor_index=monitor_index, notify=False)
    time.sleep(0.02)

    mouse_down(button)
    time.sleep(0.02)

    scheduled = generate_stroke_path(clamped_pts, duration=duration, smooth=smooth)
    for px, py, delay in scheduled:
        cx, cy = clamp_coordinates(px, py, monitor_index)
        mouse_move(cx, cy, monitor_index=monitor_index, notify=False)
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
    Executes a hardware-level mouse click (single, double, or triple)
    at the designated physical coordinates.
    If human_like=True, glides to target via Bézier trajectory with natural reaction delay.
    """
    if x is not None and y is not None:
        if human_like:
            smooth_mouse_move(x, y, speed=speed, monitor_index=monitor_index, notify=False)
            time.sleep(random.uniform(0.03, 0.07))
        else:
            mouse_move(x, y, monitor_index, notify=False)
            time.sleep(0.01)

    target_x, target_y = (x, y) if x is not None else get_cursor_position()
    _notify_indicator("click", target_x, target_y, monitor_index)

    for i in range(clicks):
        mouse_down(button)
        if human_like:
            time.sleep(random.uniform(0.06, 0.10))
        else:
            time.sleep(0.01)
        mouse_up(button)
        if i < clicks - 1:
            time.sleep(interval)


def mouse_double_click(x: Optional[int] = None, y: Optional[int] = None, monitor_index: int = 0) -> None:
    """Executes a double left click."""
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
    """Performs a smooth click-and-drag from start to end coordinates."""
    if human_like:
        mouse_stroke(
            [(start_x, start_y), (end_x, end_y)],
            button=button,
            duration=duration,
            smooth=False,
            monitor_index=monitor_index,
        )
        return

    mouse_move(start_x, start_y, monitor_index)
    time.sleep(0.02)
    mouse_down(button)
    time.sleep(0.02)

    step_delay = duration / max(1, steps)
    for s in range(1, steps + 1):
        ratio = s / float(steps)
        cur_x = int(start_x + (end_x - start_x) * ratio)
        cur_y = int(start_y + (end_y - start_y) * ratio)
        mouse_move(cur_x, cur_y, monitor_index)
        time.sleep(step_delay)

    time.sleep(0.02)
    mouse_up(button)
    _notify_indicator("drag", end_x, end_y, monitor_index)


def mouse_scroll(delta: int, horizontal: bool = False) -> None:
    """
    Scrolls the mouse wheel vertically or horizontally.
    Positive delta scrolls up/right, negative scrolls down/left.
    Standard wheel tick is 120 (WHEEL_DELTA).
    """
    ensure_dpi_aware()
    attach_input_desktop()

    flag = MOUSEEVENTF_HWHEEL if horizontal else MOUSEEVENTF_WHEEL
    # delta is usually in ticks; scale by WHEEL_DELTA (120) if small number given
    wheel_amount = delta * 120 if abs(delta) < 50 else delta

    inp = INPUT(type=INPUT_MOUSE)
    inp.mi = MOUSEINPUT(dx=0, dy=0, mouseData=wheel_amount, dwFlags=flag, time=0, dwExtraInfo=0)
    _send_inputs([inp])


def send_hotkey(keys: List[str]) -> None:
    """
    Dispatches a synchronized hotkey sequence (e.g. ['ctrl', 'shift', 'esc']).
    Presses all keys sequentially, then releases them in reverse order.
    """
    if not keys:
        return

    vk_codes: List[int] = []
    for k in keys:
        clean = k.lower().strip()
        if clean in VK_MAP:
            vk_codes.append(VK_MAP[clean])
        elif len(clean) == 1:
            # Alpha-numeric characters mapped to ASCII/VK
            ch = ord(clean.upper())
            vk_codes.append(ch)
        else:
            # Unknown key, skip
            pass

    # Press down
    down_inputs = [
        INPUT(type=INPUT_KEYBOARD, _u=_INPUT_UNION(ki=KEYBDINPUT(wVk=vk, wScan=0, dwFlags=0, time=0, dwExtraInfo=0)))
        for vk in vk_codes
    ]
    _send_inputs(down_inputs)
    time.sleep(0.02)

    # Release up in reverse
    up_inputs = [
        INPUT(type=INPUT_KEYBOARD, _u=_INPUT_UNION(ki=KEYBDINPUT(wVk=vk, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)))
        for vk in reversed(vk_codes)
    ]
    _send_inputs(up_inputs)
    _notify_indicator("hotkey")


class WindowsInputEngine(AbstractInputEngine):
    """Windows implementation of the AbstractInputEngine interface."""

    def mouse_move(self, x: int, y: int, monitor_index: int = 0) -> None:
        mouse_move(x, y, monitor_index=monitor_index)

    def mouse_down(self, button: str = "left") -> None:
        mouse_down(button=button)

    def mouse_up(self, button: str = "left") -> None:
        mouse_up(button=button)

    def mouse_click(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: str = "left",
        clicks: int = 1,
        interval: float = 0.05,
        monitor_index: int = 0,
    ) -> None:
        mouse_click(x=x, y=y, button=button, clicks=clicks, interval=interval, monitor_index=monitor_index)

    def mouse_double_click(
        self, x: Optional[int] = None, y: Optional[int] = None, monitor_index: int = 0
    ) -> None:
        mouse_double_click(x=x, y=y, monitor_index=monitor_index)

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
        mouse_drag(
            start_x=start_x,
            start_y=start_y,
            end_x=end_x,
            end_y=end_y,
            button=button,
            steps=steps,
            duration=duration,
            monitor_index=monitor_index,
        )

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
        mouse_scroll(delta=delta, horizontal=horizontal)

    def instant_type(self, text: str, press_enter: bool = False) -> None:
        instant_type(text=text, press_enter=press_enter)

    def send_hotkey(self, keys: List[str]) -> None:
        send_hotkey(keys=keys)

    def atomic_clipboard_paste(self, text: str) -> None:
        atomic_clipboard_paste(text=text)

    def execute_batch_actions(
        self, actions: List[Dict[str, Any]], auto_settle: bool = True
    ) -> Dict[str, Any]:
        return execute_batch_actions(actions=actions, auto_settle=auto_settle)


def execute_batch_actions(
    actions: List[Dict[str, Any]], auto_settle: bool = True, max_depth: int = 5
) -> Dict[str, Any]:
    """
    Executes an atomic list of hardware actions sequentially with sub-millisecond dispatch.
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
            logger.warning("Max recursion depth (%d) exceeded in batch action eval", max_depth)
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
                x = int(act.get("x", 0))
                y = int(act.get("y", 0))
                human = bool(act.get("human_like", False))
                speed = str(act.get("speed", "normal"))
                style = str(act.get("style", "bezier"))
                if human:
                    smooth_mouse_move(x, y, speed=speed, style=style)
                else:
                    mouse_move(x, y)
                step_dur = (time.perf_counter() - step_t0) * 1000.0
                executed.append({"index": current_index, "action": "move", "x": x, "y": y, "human_like": human, "duration_ms": round(step_dur, 2)})

            elif atype in ("stroke", "draw", "brush", "mouse_stroke"):
                pts = act.get("points", [])
                pts_file = act.get("points_file")
                if not pts and pts_file and os.path.isfile(pts_file):
                    try:
                        with open(pts_file, "r", encoding="utf-8") as pf:
                            pts = json.load(pf)
                    except Exception:
                        pass
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
                        x, y = int(act.get("x", 0)), int(act.get("y", 0))
                else:
                    x = int(act.get("x", 0))
                    y = int(act.get("y", 0))

                btn = str(act.get("button", "left"))
                clicks = int(act.get("clicks", 1))
                human = bool(act.get("human_like", False))
                speed = str(act.get("speed", "normal"))
                if human or speed != "normal":
                    mouse_click(x, y, button=btn, clicks=clicks, human_like=human, speed=speed)
                else:
                    mouse_click(x, y, button=btn, clicks=clicks)
                step_dur = (time.perf_counter() - step_t0) * 1000.0
                exec_item = {"index": current_index, "action": "click", "x": x, "y": y, "button": btn, "human_like": human, "duration_ms": round(step_dur, 2)}
                if target:
                    exec_item["grounded_target"] = str(target)
                executed.append(exec_item)

            elif atype in ("double_click", "dblclick"):
                x = int(act.get("x", 0))
                y = int(act.get("y", 0))
                mouse_double_click(x, y)
                step_dur = (time.perf_counter() - step_t0) * 1000.0
                executed.append({"index": current_index, "action": "double_click", "x": x, "y": y, "duration_ms": round(step_dur, 2)})

            elif atype in ("focus", "activate"):
                title = act.get("window_title")
                hwnd = act.get("hwnd")
                from extra.core.focus import find_window_by_title, force_activate_window, get_foreground_window
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

                # If focus not verified, attempt one fast fallback activation
                if not verified_focus and target_hwnd:
                    time.sleep(0.04)
                    force_activate_window(target_hwnd)
                    try:
                        fg = get_foreground_window()
                        if fg and (fg.hwnd == target_hwnd or (title and str(title).lower() in fg.title.lower())):
                            verified_focus = True
                            active_hwnd = fg.hwnd
                            active_title = fg.title
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
