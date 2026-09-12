"""
Project Extra — Win32 Hardware-Level Input Engine
Sub-millisecond SendInput execution with KEYEVENTF_UNICODE (VK_PACKET),
atomic clipboard swap, multi-button hardware mouse dispatch, and hotkeys.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import time
from typing import List, Optional, Tuple, Union

import win32clipboard
import win32con

from extra.core.geometry import (
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


def mouse_move(x: int, y: int, monitor_index: int = 0) -> None:
    """Positions the mouse cursor at exact physical display coordinates."""
    ensure_dpi_aware()
    attach_input_desktop()
    cx, cy = clamp_coordinates(x, y, monitor_index)
    user32.SetCursorPos(cx, cy)


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


def mouse_click(
    x: Optional[int] = None,
    y: Optional[int] = None,
    button: str = "left",
    clicks: int = 1,
    interval: float = 0.05,
    monitor_index: int = 0,
) -> None:
    """
    Executes a hardware-level mouse click (single, double, or triple)
    at the designated physical coordinates.
    """
    if x is not None and y is not None:
        mouse_move(x, y, monitor_index)
        time.sleep(0.01)

    for i in range(clicks):
        mouse_down(button)
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
) -> None:
    """Performs a smooth click-and-drag from start to end coordinates."""
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
