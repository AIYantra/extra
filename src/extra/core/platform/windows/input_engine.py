"""
Project Extra — Win32 Hardware-Level Input Engine
Sub-millisecond SendInput execution with KEYEVENTF_UNICODE (VK_PACKET),
atomic clipboard swap, multi-button hardware mouse dispatch, and hotkeys.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import logging
import math
import random
import time
from typing import List, Optional, Tuple, Union

import win32clipboard
import win32con

logger = logging.getLogger("extra.core.input_engine")

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


def _release_stuck_modifiers() -> None:
    """Releases any lingering modifier keys (Ctrl, Alt, Shift, Win) to avoid keystroke corruption."""
    mods = (
        win32con.VK_CONTROL, win32con.VK_LCONTROL, win32con.VK_RCONTROL,
        win32con.VK_MENU, win32con.VK_LMENU, win32con.VK_RMENU,
        win32con.VK_SHIFT, win32con.VK_LSHIFT, win32con.VK_RSHIFT,
        win32con.VK_LWIN, win32con.VK_RWIN,
    )
    for vk in mods:
        if user32.GetAsyncKeyState(vk) & 0x8000:
            ku = INPUT(type=INPUT_KEYBOARD)
            ku.ki = KEYBDINPUT(wVk=vk, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)
            _send_inputs([ku])


def instant_type(text: str, press_enter: bool = False) -> None:
    """
    Injects Unicode strings directly into the Windows input queue with atomic hardware delivery.
    Uses Win32 KEYEVENTF_UNICODE with UTF-16 code units (supporting surrogate pairs for emojis).
    Batches KeyDown and KeyUp pairs atomically to prevent WinUI 3 input buffer desynchronization.
    Translates newlines to physical Enter keystrokes to ensure 100% fidelity across native editors.
    """
    if not text and not press_enter:
        return

    _release_stuck_modifiers()

    # Normalize line endings to avoid duplicate carriage returns
    clean_text = text.replace("\r\n", "\n").replace("\r", "\n")

    for ch in clean_text:
        if ch == "\n":
            # Translate newline to physical Enter keystroke for native Win32 & WinUI edit controls
            kd_enter = INPUT(type=INPUT_KEYBOARD)
            kd_enter.ki = KEYBDINPUT(wVk=win32con.VK_RETURN, wScan=0, dwFlags=0, time=0, dwExtraInfo=0)
            ku_enter = INPUT(type=INPUT_KEYBOARD)
            ku_enter.ki = KEYBDINPUT(wVk=win32con.VK_RETURN, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)
            _send_inputs([kd_enter, ku_enter])
            time.sleep(0.003)
            continue

        # Encode character to UTF-16-LE words to capture surrogate pairs
        utf16_bytes = ch.encode("utf-16-le")
        code_units = [
            int.from_bytes(utf16_bytes[i : i + 2], "little")
            for i in range(0, len(utf16_bytes), 2)
        ]

        for unit in code_units:
            kd = INPUT(type=INPUT_KEYBOARD)
            kd.ki = KEYBDINPUT(wVk=0, wScan=unit, dwFlags=KEYEVENTF_UNICODE, time=0, dwExtraInfo=0)
            ku = INPUT(type=INPUT_KEYBOARD)
            ku.ki = KEYBDINPUT(wVk=0, wScan=unit, dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)
            # Dispatch KeyDown and KeyUp atomically together in a single OS SendInput batch
            _send_inputs([kd, ku])
            time.sleep(0.001)

    if press_enter:
        time.sleep(0.005)
        kd_enter = INPUT(type=INPUT_KEYBOARD)
        kd_enter.ki = KEYBDINPUT(wVk=win32con.VK_RETURN, wScan=0, dwFlags=0, time=0, dwExtraInfo=0)
        ku_enter = INPUT(type=INPUT_KEYBOARD)
        ku_enter.ki = KEYBDINPUT(wVk=win32con.VK_RETURN, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)
        _send_inputs([kd_enter, ku_enter])

    _notify_indicator("type")


def format_windows_cf_html(html_fragment: str) -> bytes:
    """
    Encapsulates an HTML fragment into standard Windows CF_HTML clipboard format.
    Allows rich tables, styled text, and hyperlinks to be natively parsed by
    Google Docs, Word, LibreOffice, and web rich-text editors.
    """
    header_template = (
        "Version:0.9\r\n"
        "StartHTML:{start_html:010d}\r\n"
        "EndHTML:{end_html:010d}\r\n"
        "StartFragment:{start_frag:010d}\r\n"
        "EndFragment:{end_frag:010d}\r\n"
    )
    pre = "<html><body><!--StartFragment-->"
    post = "<!--EndFragment--></body></html>"
    dummy_header = header_template.format(start_html=0, end_html=0, start_frag=0, end_frag=0)
    start_html = len(dummy_header.encode("utf-8"))
    start_frag = start_html + len(pre.encode("utf-8"))
    end_frag = start_frag + len(html_fragment.encode("utf-8"))
    end_html = end_frag + len(post.encode("utf-8"))
    final_header = header_template.format(
        start_html=start_html,
        end_html=end_html,
        start_frag=start_frag,
        end_frag=end_frag,
    )
    return (final_header + pre + html_fragment + post).encode("utf-8")


def atomic_clipboard_paste(text: str, html: Optional[str] = None, restore_delay: float = 0.05) -> None:
    """
    Safely injects text blocks, rich tables, or multi-line code snippets via clipboard:
    1. Saves current user clipboard content.
    2. Writes target text (and optional CF_HTML format) to clipboard.
    3. Triggers hardware Ctrl+V.
    4. Restores original clipboard content after restore_delay.
    """
    old_clipboard: Optional[str] = None
    try:
        win32clipboard.OpenClipboard()
        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
            old_clipboard = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
        win32clipboard.EmptyClipboard()
        if html:
            try:
                cf_html_id = win32clipboard.RegisterClipboardFormat("HTML Format")
                win32clipboard.SetClipboardData(cf_html_id, format_windows_cf_html(html))
            except Exception:
                pass
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


def get_clipboard_text(timeout: float = 0.5) -> str:
    """Safely retrieves current text payload from Windows clipboard."""
    ensure_dpi_aware()
    t_end = time.perf_counter() + timeout
    while time.perf_counter() < t_end:
        try:
            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                    data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                    return str(data or "")
                elif win32clipboard.IsClipboardFormatAvailable(win32con.CF_TEXT):
                    data = win32clipboard.GetClipboardData(win32con.CF_TEXT)
                    return data.decode("utf-8", errors="ignore") if isinstance(data, bytes) else str(data or "")
            finally:
                win32clipboard.CloseClipboard()
            return ""
        except Exception:
            time.sleep(0.03)
    return ""


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


def send_mouse_move_event(x: int, y: int, monitor_index: int = 0) -> None:
    """
    Dispatches a hardware-level MOUSEEVENTF_MOVE packet via SendInput without calling SetCursorPos.
    Essential during mouse drag and continuous strokes (MS Paint, Canva) to prevent Windows 11
    DirectManipulation / InkPresenter gesture cancellation caused by external cursor position warps.
    """
    ensure_dpi_aware()
    attach_input_desktop()
    cx, cy = clamp_coordinates(x, y, monitor_index)
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


def mouse_down(button: str = "left", x: Optional[int] = None, y: Optional[int] = None, monitor_index: int = 0) -> None:
    """Holds down the specified mouse button, optionally with explicit spatial coordinates."""
    btn = button.lower()
    flag = MOUSEEVENTF_LEFTDOWN
    if btn == "right":
        flag = MOUSEEVENTF_RIGHTDOWN
    elif btn == "middle":
        flag = MOUSEEVENTF_MIDDLEDOWN

    ensure_dpi_aware()
    attach_input_desktop()

    w = user32.GetSystemMetrics(0)
    h = user32.GetSystemMetrics(1)
    if x is not None and y is not None and w > 0 and h > 0:
        cx, cy = clamp_coordinates(x, y, monitor_index)
        nx = int(cx * 65535 / (w - 1))
        ny = int(cy * 65535 / (h - 1))
        inp = INPUT(type=INPUT_MOUSE)
        inp.mi = MOUSEINPUT(dx=nx, dy=ny, mouseData=0, dwFlags=flag | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK, time=0, dwExtraInfo=0)
        _send_inputs([inp])
    else:
        inp = INPUT(type=INPUT_MOUSE)
        inp.mi = MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=flag, time=0, dwExtraInfo=0)
        _send_inputs([inp])


def mouse_up(button: str = "left", x: Optional[int] = None, y: Optional[int] = None, monitor_index: int = 0) -> None:
    """Releases the specified mouse button, optionally with explicit spatial coordinates."""
    btn = button.lower()
    flag = MOUSEEVENTF_LEFTUP
    if btn == "right":
        flag = MOUSEEVENTF_RIGHTUP
    elif btn == "middle":
        flag = MOUSEEVENTF_MIDDLEUP

    ensure_dpi_aware()
    attach_input_desktop()

    w = user32.GetSystemMetrics(0)
    h = user32.GetSystemMetrics(1)
    if x is not None and y is not None and w > 0 and h > 0:
        cx, cy = clamp_coordinates(x, y, monitor_index)
        nx = int(cx * 65535 / (w - 1))
        ny = int(cy * 65535 / (h - 1))
        inp = INPUT(type=INPUT_MOUSE)
        inp.mi = MOUSEINPUT(dx=nx, dy=ny, mouseData=0, dwFlags=flag | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK, time=0, dwExtraInfo=0)
        _send_inputs([inp])
    else:
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
    time.sleep(0.03)

    # Hold down mouse button with explicit spatial coordinates to initiate stroke
    mouse_down(button, x=start_x, y=start_y, monitor_index=monitor_index)
    time.sleep(0.04)

    scheduled = generate_stroke_path(clamped_pts, duration=duration, smooth=smooth)
    prev_pt = (start_x, start_y)
    for px, py, delay in scheduled:
        cx, cy = clamp_coordinates(px, py, monitor_index)
        if (cx, cy) == prev_pt:
            continue
        prev_pt = (cx, cy)
        send_mouse_move_event(cx, cy, monitor_index=monitor_index)
        time.sleep(max(0.015, delay))

    time.sleep(0.04)
    last_x, last_y = clamped_pts[-1]
    mouse_up(button, x=last_x, y=last_y, monitor_index=monitor_index)
    time.sleep(0.02)
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
    time.sleep(0.03)
    mouse_down(button)
    # Hardware dwell delay: allows Windows 11 DirectManipulation / InkPresenter to establish drag contact
    time.sleep(0.05)

    step_delay = duration / max(1, steps)
    for s in range(1, steps + 1):
        ratio = s / float(steps)
        cur_x = int(start_x + (end_x - start_x) * ratio)
        cur_y = int(start_y + (end_y - start_y) * ratio)
        send_mouse_move_event(cur_x, cur_y, monitor_index=monitor_index)
        time.sleep(max(0.01, step_delay))

    time.sleep(0.03)
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

    def atomic_clipboard_paste(self, text: str, html: Optional[str] = None) -> None:
        atomic_clipboard_paste(text=text, html=html)

    def execute_batch_actions(
        self, actions: List[Dict[str, Any]], auto_settle: bool = True, auto_distill: bool = False
    ) -> Dict[str, Any]:
        return execute_batch_actions(actions=actions, auto_settle=auto_settle, auto_distill=auto_distill)


def execute_batch_actions(
    actions: List[Dict[str, Any]],
    auto_settle: bool = True,
    max_depth: int = 5,
    auto_distill: bool = False,
    max_duration_sec: float = 50.0,
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

        if explicit_ctx is None and "text" not in ctx and "distilled_ui" not in ctx:
            try:
                from extra.core.distiller import distill_screen
                d_res = distill_screen(format="compact", max_elements=25)
                ctx["text"] = d_res.content
                ctx["distilled_ui"] = d_res.content
            except Exception:
                pass
        return ctx

    def _execute_sub_list(action_list: List[Dict[str, Any]], depth: int = 0) -> bool:
        if depth > max_depth:
            logger.warning("Max recursion depth (%d) exceeded in batch action eval", max_depth)
            return True

        for act in action_list:
            if not isinstance(act, dict):
                continue
            atype = str(act.get("action", act.get("type", ""))).lower().strip()
            if not atype:
                continue

            # Hard safety deadline guard to prevent MCP client timeout (180s deadline)
            if (time.perf_counter() - t0) >= max_duration_sec:
                logger.warning(
                    "[Batch] Hard execution budget (%.1fs) reached after %d/%d actions. Pausing batch to prevent MCP timeout.",
                    max_duration_sec, len(executed), len(actions)
                )
                batch_error["partial"] = True
                batch_error["paused_at_index"] = len(executed)
                batch_error["total_actions"] = len(actions)
                batch_error["reason"] = f"Execution safely paused at {round(time.perf_counter() - t0, 1)}s to avoid MCP timeout limit."
                return False

            step_t0 = time.perf_counter()
            current_index = len(executed)

            # ── SOUL Reflexive Actions ─────────────────────────────────────
            if atype in ("decide", "eval", "condition", "branch"):
                condition = str(act.get("condition", act.get("query", "")))
                if_true = act.get("on_true", act.get("if_true", act.get("then", [])))
                if_false = act.get("on_false", act.get("if_false", act.get("else", [])))
                explicit_ctx = act.get("context")

                from extra.core.soul import get_soul_decider
                decider = get_soul_decider()
                ctx = _get_active_context(explicit_ctx)

                eval_t0 = time.perf_counter()
                decision = decider.decide_boolean(condition, context=ctx)
                eval_dur = (time.perf_counter() - eval_t0) * 1000.0

                if atype == "eval":
                    branch_name = "if_true" if decision.result else "if_false"
                else:
                    branch_name = "on_true" if decision.result else "on_false"
                branch_actions = if_true if decision.result else if_false

                executed.append({
                    "index": current_index,
                    "action": "decide" if atype == "decide" else "eval",
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

            elif atype in ("critic", "verify_milestone", "verify_acceptance", "audit_screen"):
                milestone = str(act.get("milestone", act.get("name", "batch_checkpoint")))
                expected = act.get("expected", act.get("expected_elements"))
                unwanted = act.get("unwanted", act.get("unwanted_elements"))
                custom_cond = act.get("condition")
                on_fail = str(act.get("on_fail", "abort")).lower()

                from extra.core.soul import SoulCritic
                critic = SoulCritic()
                exp_list = expected if isinstance(expected, list) else ([expected] if expected else None)
                unw_list = unwanted if isinstance(unwanted, list) else ([unwanted] if unwanted else None)
                verdict = critic.evaluate_screen_milestone(
                    milestone_name=milestone,
                    expected_elements=exp_list,
                    unwanted_elements=unw_list,
                    custom_condition=custom_cond,
                )
                step_dur = (time.perf_counter() - step_t0) * 1000.0
                executed.append({
                    "index": current_index,
                    "action": "critic",
                    "milestone": milestone,
                    "passed": verdict.passed,
                    "confidence": round(verdict.confidence, 2),
                    "defects": verdict.defects,
                    "latency_ms": round(verdict.latency_ms, 2),
                    "duration_ms": round(step_dur, 2),
                })
                if not verdict.passed and on_fail == "abort":
                    batch_error["error"] = f"SOUL-Critic milestone '{milestone}' rejected: {'; '.join(verdict.defects)}"
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
                clean_keys = [str(k).lower().strip() for k in keys]
                # Universal Win11 Anti-Snap Assist Interception:
                # Direct hardware SendInput of Win+Up triggers Windows 11 Snap Assist overlay.
                # Cleanly maximize the foreground window via Win32 SW_MAXIMIZE in <1ms!
                if clean_keys in (["win", "up"], ["super", "up"], ["windows", "up"]):
                    from extra.core.platform.windows.focus import get_foreground_window, snap_window
                    fg = get_foreground_window()
                    max_ok = False
                    if fg and fg.hwnd:
                        max_ok = snap_window(fg.hwnd, "maximize")
                    step_dur = (time.perf_counter() - step_t0) * 1000.0
                    executed.append({
                        "index": current_index,
                        "action": "hotkey",
                        "keys": keys,
                        "intercepted_maximize": True,
                        "success": max_ok,
                        "duration_ms": round(step_dur, 2),
                    })
                else:
                    send_hotkey(keys)
                    step_dur = (time.perf_counter() - step_t0) * 1000.0
                    executed.append({"index": current_index, "action": "hotkey", "keys": keys, "duration_ms": round(step_dur, 2)})

            elif atype in ("type", "text", "input"):
                text = str(act.get("text", ""))
                press_enter = bool(act.get("press_enter", False))
                instant_type(text, press_enter=press_enter)
                step_dur = (time.perf_counter() - step_t0) * 1000.0
                executed.append({"index": current_index, "action": "type", "length": len(text), "press_enter": press_enter, "duration_ms": round(step_dur, 2)})

            elif atype in ("paste", "clipboard_paste"):
                text = str(act.get("text", ""))
                html = act.get("html")
                atomic_clipboard_paste(text=text, html=html)
                step_dur = (time.perf_counter() - step_t0) * 1000.0
                executed.append({
                    "index": current_index,
                    "action": "paste",
                    "length": len(text),
                    "has_html": html is not None,
                    "duration_ms": round(step_dur, 2),
                })

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
                if act.get("canvas_relative", False):
                    try:
                        from extra.core.soul.vision_parser import detect_canvas_viewport
                        cv = detect_canvas_viewport()
                        if cv:
                            pts_tuples = [(p[0] + cv.bounding_box[0], p[1] + cv.bounding_box[1]) for p in pts_tuples]
                    except Exception:
                        pass
                if pts_tuples:
                    mouse_stroke(pts_tuples, button=btn, duration=dur, smooth=sm)
                step_dur = (time.perf_counter() - step_t0) * 1000.0
                executed.append({"index": current_index, "action": "stroke", "point_count": len(pts_tuples), "duration_ms": round(step_dur, 2)})

            elif atype in ("drag", "mouse_drag"):
                start_x = int(act.get("start_x", act.get("x1", 0)))
                start_y = int(act.get("start_y", act.get("y1", 0)))
                end_x = int(act.get("end_x", act.get("x2", 0)))
                end_y = int(act.get("end_y", act.get("y2", 0)))
                btn = str(act.get("button", "left"))
                dur = float(act.get("duration", 0.2))
                st = int(act.get("steps", 15))
                mon = int(act.get("monitor_index", 0))

                if act.get("canvas_relative", False):
                    try:
                        from extra.core.soul.vision_parser import detect_canvas_viewport
                        cv = detect_canvas_viewport()
                        if cv:
                            start_x += cv.bounding_box[0]
                            start_y += cv.bounding_box[1]
                            end_x += cv.bounding_box[0]
                            end_y += cv.bounding_box[1]
                    except Exception:
                        pass

                mouse_drag(
                    start_x=start_x,
                    start_y=start_y,
                    end_x=end_x,
                    end_y=end_y,
                    button=btn,
                    steps=st,
                    duration=dur,
                    monitor_index=mon,
                )
                step_dur = (time.perf_counter() - step_t0) * 1000.0
                executed.append({
                    "index": current_index,
                    "action": "drag",
                    "start": [start_x, start_y],
                    "end": [end_x, end_y],
                    "button": btn,
                    "duration_ms": round(step_dur, 2),
                })

            elif atype in ("click", "mouse_click"):
                target = act.get("target", act.get("query"))
                if target and ("x" not in act and "y" not in act):
                    from extra.core.soul import visual_ground
                    ground_res = visual_ground(query=str(target))
                    if ground_res.matched and ground_res.screen_point:
                        x, y = ground_res.screen_point
                    else:
                        batch_error["error"] = f"Semantic target '{target}' in batch action could not be visually grounded on screen."
                        return False
                else:
                    x = int(act.get("x", 0))
                    y = int(act.get("y", 0))
                    if act.get("canvas_relative", False):
                        try:
                            from extra.core.soul.vision_parser import detect_canvas_viewport
                            cv = detect_canvas_viewport()
                            if cv:
                                x += cv.bounding_box[0]
                                y += cv.bounding_box[1]
                        except Exception:
                            pass

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

            elif atype in ("launch", "open_app", "start_app"):
                app_name = str(act.get("app_name", act.get("app", act.get("name", ""))))
                args = act.get("args")
                maximize_arg = bool(act.get("maximize", False))
                from extra.fastpath.shell import launch_app
                l_res = launch_app(app_name=app_name, args=args, wait_for_window=True, maximize=maximize_arg)
                step_dur = (time.perf_counter() - step_t0) * 1000.0
                executed.append({
                    "index": current_index,
                    "action": "launch",
                    "app_name": app_name,
                    "maximize": maximize_arg,
                    "success": l_res.success,
                    "duration_ms": round(step_dur, 2),
                })

            elif atype in ("snap_layout", "snap", "layout"):
                lay = str(act.get("layout", "side_by_side"))
                l_win = act.get("left_window")
                r_win = act.get("right_window")
                win = act.get("window", act.get("target"))
                mon = int(act.get("monitor_index", 0))
                from extra.core.focus import snap_layout
                snap_res = snap_layout(layout=lay, left_window=l_win, right_window=r_win, window=win, monitor_index=mon)
                step_dur = (time.perf_counter() - step_t0) * 1000.0
                executed.append({
                    "index": current_index,
                    "action": "snap_layout",
                    "layout": lay,
                    "success": snap_res.get("success", False),
                    "windows": snap_res.get("windows", {}),
                    "duration_ms": round(step_dur, 2),
                })

            elif atype in ("wait_until_settled", "settle", "wait_settled"):
                timeout_sec = float(act.get("timeout_sec", act.get("timeout", 2.0)))
                from extra.core.soul.gateman import wait_until_settled
                settle_res = wait_until_settled(timeout_sec=timeout_sec)
                step_dur = (time.perf_counter() - step_t0) * 1000.0
                executed.append({
                    "index": current_index,
                    "action": "wait_until_settled",
                    "settled": settle_res.get("settled", True),
                    "duration_ms": round(step_dur, 2),
                })

            elif atype in ("read_clipboard", "copy", "get_clipboard"):
                if act.get("send_hotkey", False):
                    send_hotkey(["ctrl", "c"])
                    time.sleep(0.04)
                clip_text = get_clipboard_text()
                step_dur = (time.perf_counter() - step_t0) * 1000.0
                executed.append({
                    "index": current_index,
                    "action": "read_clipboard",
                    "value": clip_text,
                    "duration_ms": round(step_dur, 2),
                })

            elif atype in ("distill", "translate_screen", "screen_state"):
                fmt = str(act.get("format", "compact"))
                from extra.core.distiller import distill_screen
                d_res = distill_screen(format=fmt)
                step_dur = (time.perf_counter() - step_t0) * 1000.0
                executed.append({
                    "index": current_index,
                    "action": "distill",
                    "state": d_res.content,
                    "tokens": d_res.approx_tokens,
                    "duration_ms": round(step_dur, 2),
                })

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

    # Closed-Loop Reflex & Final Settle (Phase 2.1)
    final_settled = True
    if auto_settle and executed:
        last_action_item = actions[-1] if actions else {}
        has_custom_settle = "settle_ms" in last_action_item
        last_action = executed[-1].get("action", "")
        if not has_custom_settle and last_action in ("click", "double_click", "focus", "activate", "hotkey", "launch", "scroll"):
            try:
                from extra.core.soul.gateman import wait_until_settled
                s_res = wait_until_settled(timeout_sec=0.4, settle_frames=2, check_interval_ms=15)
                final_settled = s_res.get("settled", True)
            except Exception:
                pass

    total_ms = (time.perf_counter() - t0) * 1000.0
    is_success = not bool(batch_error) or batch_error.get("partial", False)
    result_dict: Dict[str, Any] = {
        "success": is_success,
        "executed_count": len(executed),
        "total_count": len(actions),
        "total_duration_ms": round(total_ms, 2),
        "actions": executed,
        "executed": executed,
        "final_settled": final_settled,
    }

    if batch_error.get("partial"):
        result_dict["partial_execution"] = True
        result_dict["remaining_count"] = batch_error.get("total_actions", len(actions)) - batch_error.get("paused_at_index", len(executed))
        result_dict["timeout_guard_applied"] = True
        result_dict["message"] = batch_error.get("reason", "Batch execution paused to prevent MCP timeout limit.")

    # Closed-Loop Active Window & Focus Telemetry
    try:
        from extra.core.focus import get_foreground_window
        fg = get_foreground_window()
        if fg:
            # Universal Windows 11 Snap Assist Auto-Neutralization:
            # If Snap Assist captured foreground focus, dismiss it with Esc to protect subsequent actions.
            if "snap assist" in fg.title.lower() or (fg.process_name and fg.process_name.lower() == "explorer.exe" and "snap" in fg.title.lower()):
                send_hotkey(["esc"])
                time.sleep(0.05)
                refreshed_fg = get_foreground_window()
                if refreshed_fg:
                    fg = refreshed_fg
                    result_dict["snap_assist_neutralized"] = True

            result_dict["active_window"] = {
                "title": fg.title,
                "hwnd": fg.hwnd,
                "process_name": fg.process_name,
            }
        else:
            result_dict["active_window"] = {
                "title": "Desktop Root",
                "hwnd": 0,
                "process_name": "explorer.exe",
            }
    except Exception as ex:
        logger.debug("Failed active window observation in batch: %s", ex)
        result_dict["active_window"] = {
            "title": "Desktop Root",
            "hwnd": 0,
            "process_name": "explorer.exe",
        }

    # Closed-Loop Clipboard Telemetry
    try:
        clip = get_clipboard_text(timeout=0.08)
        if clip:
            result_dict["clipboard"] = clip
    except Exception as ex:
        logger.debug("Failed clipboard observation in batch: %s", ex)

    # Closed-Loop Screen State Distillation (Phase 2.2)
    if auto_distill:
        try:
            from extra.core.distiller import distill_screen
            d_res = distill_screen(format="compact", max_elements=30)
            result_dict["distilled_ui"] = d_res.content
            result_dict["screen_state"] = d_res.content
        except Exception as ex:
            logger.debug("Failed screen distillation in batch: %s", ex)

    if batch_error:
        result_dict.update(batch_error)
    return result_dict
