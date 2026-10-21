"""
Project Extra — Linux Hardware-Level Input Engine
Sub-millisecond evdev /dev/uinput virtual hardware input injection,
terminal-aware atomic clipboard paste, biomechanical mouse flight,
and SOUL-governed atomic batch execution across Wayland and X11.
"""

from __future__ import annotations

import atexit
import logging
import math
import os
import random
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from extra.core.motion import (
    apply_jitter,
    generate_bezier_path,
    generate_stroke_path,
    generate_windmouse_path,
    FittsProfiler,
)
from extra.core.platform.base import AbstractInputEngine
from extra.core.platform.linux.geometry import (
    clamp_coordinates,
    get_cursor_position,
    get_virtual_screen_bounds,
    set_tracked_cursor_position,
)

logger = logging.getLogger("extra.input.linux")

# ── Evdev Virtual Device & ecodes Setup ────────────────────────────────────────

try:
    import evdev
    from evdev import AbsInfo, ecodes, UInput
    _EVDEV_AVAILABLE = True
except ImportError:
    evdev = None
    ecodes = None
    AbsInfo = None
    UInput = None
    _EVDEV_AVAILABLE = False

_uinput_device: Optional[Any] = None
_uinput_keyboard: Optional[Any] = None
_uinput_failed: bool = False
_uinput_kbd_failed: bool = False

# Terminal process and class names requiring Ctrl+Shift+V for pasting
TERMINAL_IDENTIFIERS: Set[str] = {
    "konsole",
    "alacritty",
    "kitty",
    "gnome-terminal",
    "gnome-terminal-server",
    "xterm",
    "foot",
    "foot-client",
    "terminator",
    "tilix",
    "urxvt",
    "rxvt",
    "wezterm",
    "wezterm-gui",
    "xfce4-terminal",
    "lxterminal",
    "hyper",
    "terminology",
    "contour",
}

# Universal Keymap from semantic names to Linux evdev scancodes
LINUX_KEY_MAP: Dict[str, str] = {
    # Modifiers
    "ctrl": "KEY_LEFTCTRL",
    "control": "KEY_LEFTCTRL",
    "lctrl": "KEY_LEFTCTRL",
    "rctrl": "KEY_RIGHTCTRL",
    "alt": "KEY_LEFTALT",
    "option": "KEY_LEFTALT",
    "lalt": "KEY_LEFTALT",
    "ralt": "KEY_RIGHTALT",
    "altgr": "KEY_RIGHTALT",
    "shift": "KEY_LEFTSHIFT",
    "lshift": "KEY_LEFTSHIFT",
    "rshift": "KEY_RIGHTSHIFT",
    "win": "KEY_LEFTMETA",
    "windows": "KEY_LEFTMETA",
    "meta": "KEY_LEFTMETA",
    "super": "KEY_LEFTMETA",
    "cmd": "KEY_LEFTMETA",
    "command": "KEY_LEFTMETA",
    "lwin": "KEY_LEFTMETA",
    "rwin": "KEY_RIGHTMETA",
    "menu": "KEY_COMPOSE",
    "compose": "KEY_COMPOSE",
    # System Controls
    "enter": "KEY_ENTER",
    "return": "KEY_ENTER",
    "tab": "KEY_TAB",
    "space": "KEY_SPACE",
    "backspace": "KEY_BACKSPACE",
    "delete": "KEY_DELETE",
    "del": "KEY_DELETE",
    "insert": "KEY_INSERT",
    "ins": "KEY_INSERT",
    "esc": "KEY_ESC",
    "escape": "KEY_ESC",
    "capslock": "KEY_CAPSLOCK",
    "caps": "KEY_CAPSLOCK",
    "numlock": "KEY_NUMLOCK",
    "scrolllock": "KEY_SCROLLLOCK",
    "printscreen": "KEY_SYSRQ",
    "prtscr": "KEY_SYSRQ",
    "print": "KEY_SYSRQ",
    "pause": "KEY_PAUSE",
    # Navigation
    "up": "KEY_UP",
    "down": "KEY_DOWN",
    "left": "KEY_LEFT",
    "right": "KEY_RIGHT",
    "home": "KEY_HOME",
    "end": "KEY_END",
    "pageup": "KEY_PAGEUP",
    "pgup": "KEY_PAGEUP",
    "pagedown": "KEY_PAGEDOWN",
    "pgdn": "KEY_PAGEDOWN",
    # Function Keys
    "f1": "KEY_F1",
    "f2": "KEY_F2",
    "f3": "KEY_F3",
    "f4": "KEY_F4",
    "f5": "KEY_F5",
    "f6": "KEY_F6",
    "f7": "KEY_F7",
    "f8": "KEY_F8",
    "f9": "KEY_F9",
    "f10": "KEY_F10",
    "f11": "KEY_F11",
    "f12": "KEY_F12",
    # Digits
    "0": "KEY_0",
    "1": "KEY_1",
    "2": "KEY_2",
    "3": "KEY_3",
    "4": "KEY_4",
    "5": "KEY_5",
    "6": "KEY_6",
    "7": "KEY_7",
    "8": "KEY_8",
    "9": "KEY_9",
    # Letters
    "a": "KEY_A",
    "b": "KEY_B",
    "c": "KEY_C",
    "d": "KEY_D",
    "e": "KEY_E",
    "f": "KEY_F",
    "g": "KEY_G",
    "h": "KEY_H",
    "i": "KEY_I",
    "j": "KEY_J",
    "k": "KEY_K",
    "l": "KEY_L",
    "m": "KEY_M",
    "n": "KEY_N",
    "o": "KEY_O",
    "p": "KEY_P",
    "q": "KEY_Q",
    "r": "KEY_R",
    "s": "KEY_S",
    "t": "KEY_T",
    "u": "KEY_U",
    "v": "KEY_V",
    "w": "KEY_W",
    "x": "KEY_X",
    "y": "KEY_Y",
    "z": "KEY_Z",
    # Punctuation & Symbols
    "-": "KEY_MINUS",
    "minus": "KEY_MINUS",
    "=": "KEY_EQUAL",
    "equal": "KEY_EQUAL",
    "equals": "KEY_EQUAL",
    "*": "KEY_KPASTERISK",
    "asterisk": "KEY_KPASTERISK",
    "+": "KEY_KPPLUS",
    "plus": "KEY_KPPLUS",
    "[": "KEY_LEFTBRACE",
    "bracketleft": "KEY_LEFTBRACE",
    "]": "KEY_RIGHTBRACE",
    "bracketright": "KEY_RIGHTBRACE",
    ";": "KEY_SEMICOLON",
    "semicolon": "KEY_SEMICOLON",
    "'": "KEY_APOSTROPHE",
    "quote": "KEY_APOSTROPHE",
    "apostrophe": "KEY_APOSTROPHE",
    "`": "KEY_GRAVE",
    "grave": "KEY_GRAVE",
    "\\": "KEY_BACKSLASH",
    "backslash": "KEY_BACKSLASH",
    ",": "KEY_COMMA",
    "comma": "KEY_COMMA",
    ".": "KEY_DOT",
    "period": "KEY_DOT",
    "dot": "KEY_DOT",
    "/": "KEY_SLASH",
    "slash": "KEY_SLASH",
    # Numpad
    "numpad0": "KEY_KP0",
    "numpad1": "KEY_KP1",
    "numpad2": "KEY_KP2",
    "numpad3": "KEY_KP3",
    "numpad4": "KEY_KP4",
    "numpad5": "KEY_KP5",
    "numpad6": "KEY_KP6",
    "numpad7": "KEY_KP7",
    "numpad8": "KEY_KP8",
    "numpad9": "KEY_KP9",
    "add": "KEY_KPPLUS",
    "subtract": "KEY_KPMINUS",
    "multiply": "KEY_KPASTERISK",
    "divide": "KEY_KPSLASH",
    "decimal": "KEY_KPDOT",
    "numpadenter": "KEY_KPENTER",
}


def _cleanup_uinput() -> None:
    """Closes the persistent uinput virtual devices on exit."""
    global _uinput_device, _uinput_keyboard
    for dev in (_uinput_device, _uinput_keyboard):
        if dev is not None:
            try:
                dev.close()
            except Exception:
                pass
    _uinput_device = None
    _uinput_keyboard = None


atexit.register(_cleanup_uinput)


def get_uinput_device() -> Optional[Any]:
    """
    Retrieves or instantiates the singleton kernel uinput virtual pointer device.
    Supports absolute pointer coordinates, relative wheel scrolling, and mouse buttons.
    """
    global _uinput_device, _uinput_failed
    if _uinput_device is not None:
        return _uinput_device
    if _uinput_failed or not _EVDEV_AVAILABLE:
        return None

    try:
        _, _, width, height = get_virtual_screen_bounds()
        max_x = max(1, width - 1) if width > 0 else 1920
        max_y = max(1, height - 1) if height > 0 else 1080

        mouse_buttons = [
            ecodes.BTN_LEFT,
            ecodes.BTN_RIGHT,
            ecodes.BTN_MIDDLE,
            ecodes.BTN_SIDE,
            ecodes.BTN_EXTRA,
        ]

        capabilities = {
            ecodes.EV_KEY: mouse_buttons,
            ecodes.EV_ABS: [
                (ecodes.ABS_X, AbsInfo(value=0, min=0, max=max_x, fuzz=0, flat=0, resolution=1)),
                (ecodes.ABS_Y, AbsInfo(value=0, min=0, max=max_y, fuzz=0, flat=0, resolution=1)),
            ],
            ecodes.EV_REL: [
                ecodes.REL_X,
                ecodes.REL_Y,
                ecodes.REL_WHEEL,
                ecodes.REL_HWHEEL,
            ],
        }

        ui = UInput(capabilities, name="Extra-Virtual-Pointer")
        _uinput_device = ui
        time.sleep(0.15)
        logger.debug("Initialized Extra virtual pointer at %s", getattr(ui.device, "path", "/dev/uinput"))
        return _uinput_device
    except Exception as exc:
        logger.warning("Failed to initialize kernel pointer device (%s). Falling back to xdotool.", exc)
        _uinput_failed = True
        return None


def get_uinput_keyboard() -> Optional[Any]:
    """
    Retrieves or instantiates the singleton kernel uinput virtual keyboard device.
    Supports standard hardware keyboard scancodes for 100% desktop fidelity.
    """
    global _uinput_keyboard, _uinput_kbd_failed
    if _uinput_keyboard is not None:
        return _uinput_keyboard
    if _uinput_kbd_failed or not _EVDEV_AVAILABLE:
        return None

    try:
        valid_keys: List[int] = []
        for name in dir(ecodes):
            if name.startswith("KEY_") and not name.endswith("_MAX") and not name.endswith("_CNT"):
                val = getattr(ecodes, name)
                if isinstance(val, int) and 0 < val < 0x2ff:
                    valid_keys.append(val)
        valid_keys = list(set(valid_keys))

        capabilities = {
            ecodes.EV_KEY: valid_keys,
        }

        kbd = UInput(capabilities, name="Extra-Virtual-Keyboard")
        _uinput_keyboard = kbd
        time.sleep(0.15)
        logger.debug("Initialized Extra virtual keyboard at %s", getattr(kbd.device, "path", "/dev/uinput"))
        return _uinput_keyboard
    except Exception as exc:
        logger.warning("Failed to initialize kernel keyboard device (%s). Falling back to xdotool/clipboard.", exc)
        _uinput_kbd_failed = True
        return None


def _notify_indicator(
    action: str,
    x: Optional[int] = None,
    y: Optional[int] = None,
    monitor_index: int = 0,
) -> None:
    """Helper to dispatch real-time feedback to indicator controller without latency."""
    try:
        from extra.core.platform.linux.indicators import get_indicator_controller
        get_indicator_controller().task_action(
            action_type=action, x=x or 0, y=y or 0, monitor_index=monitor_index
        )
    except Exception:
        pass


def _resolve_button_code(button: str) -> Tuple[Optional[int], str]:
    """Resolves button string to (evdev_code, xdotool_btn_str)."""
    btn = button.lower().strip()
    if btn in ("left", "l"):
        code = getattr(ecodes, "BTN_LEFT", 0x110) if ecodes else 0x110
        return code, "1"
    elif btn in ("right", "r"):
        code = getattr(ecodes, "BTN_RIGHT", 0x111) if ecodes else 0x111
        return code, "3"
    elif btn in ("middle", "m"):
        code = getattr(ecodes, "BTN_MIDDLE", 0x112) if ecodes else 0x112
        return code, "2"
    elif btn in ("side", "back"):
        code = getattr(ecodes, "BTN_SIDE", 0x115) if ecodes else 0x115
        return code, "8"
    elif btn in ("extra", "forward"):
        code = getattr(ecodes, "BTN_EXTRA", 0x116) if ecodes else 0x116
        return code, "9"
    # Default to left
    code = getattr(ecodes, "BTN_LEFT", 0x110) if ecodes else 0x110
    return code, "1"


# ── Mouse Input Primitives ─────────────────────────────────────────────────────

def mouse_move(x: int, y: int, monitor_index: int = 0, notify: bool = True) -> None:
    """
    Dispatches hardware mouse cursor movement to physical coordinates (x, y).
    Uses kernel /dev/uinput absolute positioning (ABS_X, ABS_Y) for exact
    sub-pixel accuracy across Wayland and X11, with xdotool fallback.
    """
    cx, cy = clamp_coordinates(x, y, monitor_index)
    ui = get_uinput_device()

    if ui is not None and ecodes is not None:
        try:
            ui.write(ecodes.EV_ABS, ecodes.ABS_X, cx)
            ui.write(ecodes.EV_ABS, ecodes.ABS_Y, cy)
            ui.syn()
        except Exception as ex:
            logger.debug("uinput mouse_move write error: %s", ex)

    # Secondary / XWayland sync
    if shutil.which("xdotool"):
        try:
            subprocess.run(
                ["xdotool", "mousemove", str(cx), str(cy)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=0.1,
            )
        except Exception:
            pass

    set_tracked_cursor_position(cx, cy)
    if notify:
        _notify_indicator("move", cx, cy, monitor_index)


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
    Glides the mouse cursor to (x, y) along a human-like biomechanical trajectory
    with randomized micro-jitter, physiological tremor emulation, and target deceleration.
    """
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
        ox_pt = (
            FittsProfiler.generate_overshoot((start_x, start_y), (target_x, target_y), distance)
            if overshoot
            else None
        )
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
        mouse_move(cx, cy, monitor_index=monitor_index, notify=False)
        time.sleep(delay)

    mouse_move(target_x, target_y, monitor_index=monitor_index, notify=notify)


def mouse_down(button: str = "left") -> None:
    """Depresses a mouse button."""
    btn_code, btn_str = _resolve_button_code(button)
    ui = get_uinput_device()

    if ui is not None and ecodes is not None and btn_code is not None:
        try:
            ui.write(ecodes.EV_KEY, btn_code, 1)
            ui.syn()
            return
        except Exception as ex:
            logger.debug("uinput mouse_down error: %s", ex)

    if shutil.which("xdotool"):
        try:
            subprocess.run(
                ["xdotool", "mousedown", btn_str],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=0.1,
            )
        except Exception:
            pass


def mouse_up(button: str = "left") -> None:
    """Releases a mouse button."""
    btn_code, btn_str = _resolve_button_code(button)
    ui = get_uinput_device()

    if ui is not None and ecodes is not None and btn_code is not None:
        try:
            ui.write(ecodes.EV_KEY, btn_code, 0)
            ui.syn()
            return
        except Exception as ex:
            logger.debug("uinput mouse_up error: %s", ex)

    if shutil.which("xdotool"):
        try:
            subprocess.run(
                ["xdotool", "mouseup", btn_str],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=0.1,
            )
        except Exception:
            pass


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
            mouse_move(x, y, monitor_index=monitor_index, notify=False)
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


def mouse_double_click(
    x: Optional[int] = None, y: Optional[int] = None, monitor_index: int = 0
) -> None:
    """Executes a double left click."""
    mouse_click(x=x, y=y, button="left", clicks=2, interval=0.06, monitor_index=monitor_index)


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

    mouse_move(start_x, start_y, monitor_index=monitor_index)
    time.sleep(0.02)
    mouse_down(button)
    time.sleep(0.02)

    step_delay = duration / max(1, steps)
    for s in range(1, steps + 1):
        ratio = s / float(steps)
        cur_x = int(start_x + (end_x - start_x) * ratio)
        cur_y = int(start_y + (end_y - start_y) * ratio)
        mouse_move(cur_x, cur_y, monitor_index=monitor_index, notify=False)
        time.sleep(step_delay)

    time.sleep(0.02)
    mouse_up(button)
    _notify_indicator("drag", end_x, end_y, monitor_index)


def mouse_stroke(
    points: List[Tuple[int, int]],
    button: str = "left",
    duration: float = 1.0,
    smooth: bool = True,
    monitor_index: int = 0,
) -> None:
    """
    Executes a continuous smooth brush stroke across multiple waypoints while holding button.
    Dispatches hardware dwell delay for canvas drag contact and inking engagement.
    """
    if not points:
        return

    clamped_pts = [clamp_coordinates(p[0], p[1], monitor_index) for p in points]
    if len(clamped_pts) == 1:
        mouse_click(clamped_pts[0][0], clamped_pts[0][1], button=button, monitor_index=monitor_index)
        return

    start_x, start_y = clamped_pts[0]
    mouse_move(start_x, start_y, monitor_index=monitor_index, notify=False)
    time.sleep(0.05)

    mouse_down(button)
    # Hardware dwell delay: allows Wayland / X11 inking presenters to establish drag contact
    time.sleep(0.06)

    scheduled = generate_stroke_path(clamped_pts, duration=duration, smooth=smooth)
    prev_pt = (start_x, start_y)
    for px, py, delay in scheduled:
        cx, cy = clamp_coordinates(px, py, monitor_index)
        if (cx, cy) == prev_pt:
            continue
        prev_pt = (cx, cy)
        mouse_move(cx, cy, monitor_index=monitor_index, notify=False)
        time.sleep(max(0.015, delay))

    time.sleep(0.05)
    mouse_up(button)
    time.sleep(0.02)
    last_x, last_y = clamped_pts[-1]
    _notify_indicator("drag", last_x, last_y, monitor_index)


def mouse_scroll(delta: int, horizontal: bool = False) -> None:
    """
    Scrolls the mouse wheel vertically or horizontally.
    Positive delta scrolls up/right, negative scrolls down/left.
    """
    ui = get_uinput_device()
    ticks = delta // 120 if abs(delta) >= 120 else delta
    if ticks == 0:
        ticks = 1 if delta > 0 else -1

    if ui is not None and ecodes is not None:
        try:
            rel_code = ecodes.REL_HWHEEL if horizontal else ecodes.REL_WHEEL
            ui.write(ecodes.EV_REL, rel_code, ticks)
            ui.syn()
            return
        except Exception as ex:
            logger.debug("uinput mouse_scroll error: %s", ex)

    # Fallback to xdotool
    if shutil.which("xdotool"):
        try:
            if horizontal:
                btn = "7" if ticks > 0 else "6"
            else:
                btn = "4" if ticks > 0 else "5"
            for _ in range(abs(ticks)):
                subprocess.run(
                    ["xdotool", "click", btn],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=0.1,
                )
        except Exception:
            pass


# ── Keyboard & Hotkey Primitives ───────────────────────────────────────────────

def _resolve_key_scancode(key_name: str) -> Optional[int]:
    """Resolves semantic key name to Linux evdev scancode integer."""
    if not ecodes:
        return None
    normalized = key_name.lower().strip()
    ecode_name = LINUX_KEY_MAP.get(normalized)
    if ecode_name and hasattr(ecodes, ecode_name):
        return getattr(ecodes, ecode_name)

    # Direct KEY_* probe
    direct_name = f"KEY_{normalized.upper()}"
    if hasattr(ecodes, direct_name):
        return getattr(ecodes, direct_name)

    return None


def send_hotkey(keys: List[str]) -> None:
    """
    Dispatches a synchronized hotkey sequence (e.g. ['ctrl', 'shift', 't']).
    Presses all keys sequentially, then releases them in reverse order.
    """
    if not keys:
        return

    ui = get_uinput_keyboard()
    codes: List[int] = []

    if ui is not None and ecodes is not None:
        all_resolved = True
        for k in keys:
            code = _resolve_key_scancode(k)
            if code is not None:
                codes.append(code)
            else:
                all_resolved = False
                break

        if all_resolved and codes:
            try:
                # Key downs in order
                for c in codes:
                    ui.write(ecodes.EV_KEY, c, 1)
                    ui.syn()
                    time.sleep(0.01)
                time.sleep(0.02)
                # Key ups in reverse order
                for c in reversed(codes):
                    ui.write(ecodes.EV_KEY, c, 0)
                    ui.syn()
                    time.sleep(0.01)
                _notify_indicator("hotkey")
                return
            except Exception as ex:
                logger.debug("uinput send_hotkey error: %s", ex)

    # Fallback to xdotool
    if shutil.which("xdotool"):
        try:
            # Map semantic keys to xdotool key format
            xkeys = []
            for k in keys:
                kn = k.lower().strip()
                if kn in ("ctrl", "control"):
                    xkeys.append("ctrl")
                elif kn in ("alt", "option"):
                    xkeys.append("alt")
                elif kn in ("shift",):
                    xkeys.append("shift")
                elif kn in ("super", "win", "windows", "meta", "cmd"):
                    xkeys.append("super")
                elif kn in ("enter", "return"):
                    xkeys.append("Return")
                elif kn in ("esc", "escape"):
                    xkeys.append("Escape")
                else:
                    xkeys.append(kn)
            combo = "+".join(xkeys)
            subprocess.run(
                ["xdotool", "key", combo],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=0.5,
            )
            _notify_indicator("hotkey")
        except Exception:
            pass


def is_active_window_terminal() -> bool:
    """
    Detects if the currently focused foreground window is a terminal emulator
    requiring Ctrl+Shift+V for clipboard pasting.
    """
    try:
        from extra.core.platform.linux.focus import get_foreground_window
        fg = get_foreground_window()
        if fg:
            proc = (fg.process_name or "").lower().strip()
            cls = (fg.class_name or "").lower().strip()
            for term in TERMINAL_IDENTIFIERS:
                if term in proc or term in cls:
                    return True
    except Exception:
        pass
    return False


def atomic_clipboard_paste(text: str, html: Optional[str] = None, restore_delay: float = 0.05) -> None:
    """
    Safely injects massive text blocks or multi-line code snippets via clipboard:
    1. Saves existing clipboard contents (wl-paste or xclip).
    2. Writes target text atomically (wl-copy or xclip).
    3. Terminal Discrimination: dispatches Ctrl+Shift+V for terminals, Ctrl+V for GUI.
    4. Restores original clipboard contents within restore_delay.
    """
    is_term = is_active_window_terminal()
    paste_keys = ["ctrl", "shift", "v"] if is_term else ["ctrl", "v"]

    # 1. Wayland clipboard pipeline (wl-copy / wl-paste)
    if shutil.which("wl-copy") and shutil.which("wl-paste"):
        old_clip: Optional[str] = None
        try:
            old_clip = subprocess.check_output(
                ["wl-paste", "--no-newline"], stderr=subprocess.DEVNULL, timeout=0.3
            ).decode("utf-8", errors="replace")
        except Exception:
            pass

        try:
            p = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE)
            p.communicate(input=text.encode("utf-8"), timeout=0.5)
            time.sleep(0.02)
            send_hotkey(paste_keys)
            time.sleep(restore_delay)
        finally:
            if old_clip is not None:
                try:
                    p = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE)
                    p.communicate(input=old_clip.encode("utf-8"), timeout=0.3)
                except Exception:
                    pass
        return

    # 2. X11 clipboard pipeline (xclip)
    if shutil.which("xclip"):
        old_clip = None
        try:
            old_clip = subprocess.check_output(
                ["xclip", "-selection", "clipboard", "-o"],
                stderr=subprocess.DEVNULL,
                timeout=0.3,
            ).decode("utf-8", errors="replace")
        except Exception:
            pass

        try:
            p = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
            p.communicate(input=text.encode("utf-8"), timeout=0.5)
            time.sleep(0.02)
            send_hotkey(paste_keys)
            time.sleep(restore_delay)
        finally:
            if old_clip is not None:
                try:
                    p = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
                    p.communicate(input=old_clip.encode("utf-8"), timeout=0.3)
                except Exception:
                    pass
        return

    # 3. Direct xdotool type fallback
    if shutil.which("xdotool"):
        try:
            subprocess.run(
                ["xdotool", "type", "--delay", "5", "--", text],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2.0,
            )
        except Exception:
            pass


def instant_type(text: str, press_enter: bool = False) -> None:
    """
    Injects Unicode text directly into the active application.
    For multi-character or Unicode text, uses terminal-aware atomic clipboard paste.
    For short alphanumeric sequences, dispatches hardware keyboard scancodes.
    """
    if not text and not press_enter:
        return

    if text:
        ui = get_uinput_keyboard()
        typed_via_uinput = False
        all_mappable = ui is not None and ecodes is not None and all(_resolve_key_scancode(c) is not None for c in text)

        if all_mappable:
            try:
                for char in text:
                    code = _resolve_key_scancode(char)
                    if code is not None:
                        ui.write(ecodes.EV_KEY, code, 1)
                        ui.syn()
                        time.sleep(0.005)
                        ui.write(ecodes.EV_KEY, code, 0)
                        ui.syn()
                        time.sleep(0.005)
                typed_via_uinput = True
            except Exception:
                typed_via_uinput = False

        if not typed_via_uinput:
            if shutil.which("xdotool"):
                try:
                    subprocess.run(
                        ["xdotool", "type", "--delay", "5", "--", text],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=0.5,
                    )
                    typed_via_uinput = True
                except Exception:
                    pass

        if not typed_via_uinput:
            atomic_clipboard_paste(text)

    if press_enter:
        send_hotkey(["enter"])

    _notify_indicator("type")


# ── SOUL-Governed Atomic Batch Actions ─────────────────────────────────────────

def execute_batch_actions(
    actions: List[Dict[str, Any]], auto_settle: bool = True, auto_distill: bool = True
) -> Dict[str, Any]:
    """
    Executes an atomic list of hardware actions sequentially with sub-millisecond dispatch
    and optional Tier 1 visual settle in a single tool turn.
    Supports Project SOUL dynamic reflex conditions ('eval', 'assert', 'wait_for_state').
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
                    ctx["process_name"] = getattr(fg, "class_name", "") or str(getattr(fg, "process_id", ""))
            except Exception:
                pass

        if "text" not in ctx and "distilled_ui" not in ctx:
            try:
                from extra.core.distiller import distill_screen
                d_res = distill_screen(format="compact", max_elements=25)
                ctx["text"] = d_res.content
                ctx["distilled_ui"] = d_res.content
            except Exception:
                pass
        return ctx

    def _execute_sub_list(action_list: List[Dict[str, Any]], depth: int = 0) -> bool:
        if depth > 5:
            batch_error["error"] = "Maximum batch action nesting depth (5) exceeded."
            return False

        for act in action_list:
            if not isinstance(act, dict):
                continue

            step_t0 = time.perf_counter()
            atype = str(act.get("action", act.get("type", ""))).lower().strip()
            current_index = len(executed)

            # ── Project SOUL Dynamic Reflex Controls ───────────────────────
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
                    "confidence": round(decision.confidence, 3),
                    "branch": branch_name,
                    "sub_actions_count": len(branch_actions) if isinstance(branch_actions, list) else 0,
                    "duration_ms": round(eval_dur, 2),
                })

                if isinstance(branch_actions, list) and branch_actions:
                    if not _execute_sub_list(branch_actions, depth=depth + 1):
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
                explicit_ctx = act.get("context")
                on_fail = str(act.get("on_fail", "abort")).lower()
                retry_actions = act.get("retry_actions", [])
                max_retries = int(act.get("max_retries", 1))

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
                executed.append({
                    "index": current_index,
                    "action": "hotkey",
                    "keys": keys,
                    "duration_ms": round(step_dur, 2),
                })

            elif atype in ("type", "text", "input"):
                text = str(act.get("text", ""))
                press_enter = bool(act.get("press_enter", False))
                instant_type(text, press_enter=press_enter)
                step_dur = (time.perf_counter() - step_t0) * 1000.0
                executed.append({
                    "index": current_index,
                    "action": "type",
                    "length": len(text),
                    "press_enter": press_enter,
                    "duration_ms": round(step_dur, 2),
                })

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
                executed.append({
                    "index": current_index,
                    "action": "move",
                    "x": x,
                    "y": y,
                    "human_like": human,
                    "duration_ms": round(step_dur, 2),
                })

            elif atype in ("stroke", "draw", "brush"):
                pts = act.get("points", [])
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
                executed.append({
                    "index": current_index,
                    "action": "stroke",
                    "point_count": len(pts_tuples),
                    "duration_ms": round(step_dur, 2),
                })

            elif atype in ("drag", "mouse_drag"):
                start_x = int(act.get("start_x", act.get("x1", 0)))
                start_y = int(act.get("start_y", act.get("y1", 0)))
                end_x = int(act.get("end_x", act.get("x2", 0)))
                end_y = int(act.get("end_y", act.get("y2", 0)))
                btn = str(act.get("button", "left"))
                dur = float(act.get("duration", 0.2))
                st = int(act.get("steps", 15))

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
                        x, y = act.get("x"), act.get("y")
                else:
                    x = act.get("x")
                    y = act.get("y")
                    if act.get("canvas_relative", False) and x is not None and y is not None:
                        try:
                            from extra.core.soul.vision_parser import detect_canvas_viewport
                            cv = detect_canvas_viewport()
                            if cv:
                                x = int(x) + cv.bounding_box[0]
                                y = int(y) + cv.bounding_box[1]
                        except Exception:
                            pass

                btn = str(act.get("button", "left"))

                clicks = int(act.get("clicks", 1))
                human = bool(act.get("human_like", False))
                speed = str(act.get("speed", "normal"))
                if human:
                    mouse_click(
                        int(x) if x is not None else None,
                        int(y) if y is not None else None,
                        button=btn,
                        clicks=clicks,
                        human_like=human,
                        speed=speed,
                    )
                else:
                    mouse_click(
                        int(x) if x is not None else None,
                        int(y) if y is not None else None,
                        button=btn,
                        clicks=clicks,
                    )
                step_dur = (time.perf_counter() - step_t0) * 1000.0
                exec_item: Dict[str, Any] = {
                    "index": current_index,
                    "action": "click",
                    "x": x,
                    "y": y,
                    "button": btn,
                    "human_like": human,
                    "duration_ms": round(step_dur, 2),
                }
                if target:
                    exec_item["grounded_target"] = str(target)
                executed.append(exec_item)

            elif atype in ("double_click", "dblclick"):
                x = act.get("x")
                y = act.get("y")
                mouse_double_click(
                    int(x) if x is not None else None,
                    int(y) if y is not None else None,
                )
                step_dur = (time.perf_counter() - step_t0) * 1000.0
                executed.append({
                    "index": current_index,
                    "action": "double_click",
                    "x": x,
                    "y": y,
                    "duration_ms": round(step_dur, 2),
                })

            elif atype in ("focus", "activate"):
                title = act.get("window_title")
                hwnd = act.get("hwnd")
                from extra.core.focus import (
                    find_window_by_title,
                    force_activate_window,
                    get_foreground_window,
                )
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
                    ms = int(
                        act.get(
                            "ms",
                            act.get(
                                "duration_ms",
                                act.get("delay", act.get("delay_ms", act.get("duration", 100))),
                            ),
                        )
                    )
                time.sleep(ms / 1000.0)
                executed.append({"index": current_index, "action": "sleep", "ms": ms})

            elif atype in ("scroll", "wheel"):
                clicks = int(act.get("clicks", 1))
                direction = str(act.get("direction", "vertical"))
                mouse_scroll(delta=clicks * 120, horizontal=(direction.lower() == "horizontal"))
                step_dur = (time.perf_counter() - step_t0) * 1000.0
                executed.append({
                    "index": current_index,
                    "action": "scroll",
                    "clicks": clicks,
                    "direction": direction,
                    "duration_ms": round(step_dur, 2),
                })

            elif atype in ("launch", "open_app", "start_app"):
                app_name = str(act.get("app_name", act.get("app", act.get("name", ""))))
                args = act.get("args")
                from extra.core.platform.linux.shell import launch_app
                l_res = launch_app(app_name=app_name, args=args)
                step_dur = (time.perf_counter() - step_t0) * 1000.0
                executed.append({
                    "index": current_index,
                    "action": "launch",
                    "app_name": app_name,
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
                snap_res = snap_layout(layout=lay, left_window=l_win, right_window=r_win, monitor_index=mon)
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
                clip_text = ""
                try:
                    import subprocess
                    for cmd in (["wl-paste"], ["xclip", "-selection", "clipboard", "-o"], ["xsel", "--clipboard", "--output"]):
                        if shutil.which(cmd[0]):
                            c_proc = subprocess.run(cmd, capture_output=True, text=True, timeout=0.5)
                            if c_proc.returncode == 0:
                                clip_text = c_proc.stdout
                                break
                except Exception:
                    pass
                step_dur = (time.perf_counter() - step_t0) * 1000.0
                executed.append({
                    "index": current_index,
                    "action": "read_clipboard",
                    "value": clip_text,
                    "duration_ms": round(step_dur, 2),
                })

            # Tier 1 In-Memory Visual Settle / Physical Action Delay
            if "settle_ms" in act:
                time.sleep(int(act["settle_ms"]) / 1000.0)
            elif auto_settle and atype in ("click", "double_click", "focus", "activate", "hotkey", "scroll"):
                try:
                    from extra.core.soul.gateman import wait_until_settled
                    settle_res = wait_until_settled(timeout_sec=0.4, settle_frames=2, check_interval_ms=15)
                    if executed:
                        executed[-1]["settled"] = settle_res.get("settled", True)
                        executed[-1]["settle_ms"] = round(settle_res.get("duration_ms", 0.0), 2)
                except Exception:
                    time.sleep(0.02)
            else:
                default_settle = (
                    0
                    if atype
                    in (
                        "eval",
                        "condition",
                        "branch",
                        "assert",
                        "check",
                        "wait_for_state",
                        "wait_until",
                        "poll_state",
                        "sleep",
                        "wait",
                        "pause",
                    )
                    else 30
                )
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
    result_dict: Dict[str, Any] = {
        "success": not bool(batch_error),
        "executed_count": len(executed),
        "total_duration_ms": round(total_ms, 2),
        "actions": executed,
        "executed": executed,
        "final_settled": final_settled,
    }

    # Closed-Loop Active Window & Focus Telemetry
    try:
        from extra.core.focus import get_foreground_window
        fg = get_foreground_window()
        if fg:
            result_dict["active_window"] = {
                "title": fg.title,
                "hwnd": getattr(fg, "hwnd", 0),
                "process_name": getattr(fg, "process_name", ""),
            }
        else:
            result_dict["active_window"] = {
                "title": "Desktop Root",
                "hwnd": 0,
                "process_name": "desktop",
            }
    except Exception:
        result_dict["active_window"] = {
            "title": "Desktop Root",
            "hwnd": 0,
            "process_name": "desktop",
        }

    # Closed-Loop Screen State Distillation (Phase 2.2)
    if auto_distill:
        try:
            from extra.core.distiller import distill_screen
            d_res = distill_screen(format="compact", max_elements=30)
            result_dict["distilled_ui"] = d_res.content
            result_dict["screen_state"] = d_res.content
        except Exception:
            pass

    if batch_error:
        result_dict.update(batch_error)
    return result_dict


# ── LinuxInputEngine Class Implementation ──────────────────────────────────────

class LinuxInputEngine(AbstractInputEngine):
    """Linux implementation of AbstractInputEngine."""

    def mouse_move(self, x: int, y: int, monitor_index: int = 0) -> None:
        mouse_move(x, y, monitor_index=monitor_index)

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
            x,
            y,
            speed=speed,
            style=style,
            monitor_index=monitor_index,
            overshoot=overshoot,
        )

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
        mouse_click(
            x=x,
            y=y,
            button=button,
            clicks=clicks,
            interval=interval,
            monitor_index=monitor_index,
        )

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
            start_x,
            start_y,
            end_x,
            end_y,
            button=button,
            steps=steps,
            duration=duration,
            monitor_index=monitor_index,
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
            points,
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

    def atomic_clipboard_paste(self, text: str, html: Optional[str] = None) -> None:
        atomic_clipboard_paste(text, html=html)

    def execute_batch_actions(
        self, actions: List[Dict[str, Any]], auto_settle: bool = True, auto_distill: bool = True
    ) -> Dict[str, Any]:
        return execute_batch_actions(actions, auto_settle=auto_settle, auto_distill=auto_distill)


InputEngine = LinuxInputEngine
