"""
Project Extra — Linux Platform Input Engine Unit Tests
Tests uinput virtual hardware device, key scancode mappings,
mouse motion, clicks, drags, strokes, terminal discrimination,
instant typing, and SOUL batch execution on Linux.
"""

from __future__ import annotations

import sys
import unittest
from unittest.mock import MagicMock, patch

if not sys.platform.startswith("linux"):
    raise unittest.SkipTest("Linux-specific input tests skipped on non-Linux")

from extra.core.platform.base import AbstractInputEngine
from extra.core.platform.linux.input_engine import (
    LinuxInputEngine,
    _resolve_button_code,
    _resolve_key_scancode,
    atomic_clipboard_paste,
    execute_batch_actions,
    get_uinput_device,
    instant_type,
    is_active_window_terminal,
    mouse_click,
    mouse_double_click,
    mouse_down,
    mouse_drag,
    mouse_move,
    mouse_scroll,
    mouse_stroke,
    mouse_up,
    send_hotkey,
    smooth_mouse_move,
)


class TestLinuxInputEngine(unittest.TestCase):
    """Exhaustive tests for Linux hardware input engine and inking primitives."""

    def setUp(self) -> None:
        self.engine = LinuxInputEngine()

    def test_abstract_interface_conformance(self) -> None:
        """Verify LinuxInputEngine strictly conforms to AbstractInputEngine interface."""
        self.assertIsInstance(self.engine, AbstractInputEngine)

    def test_uinput_device_or_fallback(self) -> None:
        """Verify uinput device initialization attempts or falls back cleanly."""
        ui = get_uinput_device()
        # On systems with /dev/uinput permissions, ui is an evdev UInput object;
        # in restricted environments it gracefully returns None.
        if ui is not None:
            self.assertTrue(hasattr(ui, "write"))
            self.assertTrue(hasattr(ui, "syn"))

    def test_key_scancode_resolution(self) -> None:
        """Verify semantic keys resolve to valid evdev scancodes."""
        test_keys = [
            "ctrl", "shift", "alt", "win", "super", "meta",
            "enter", "return", "tab", "space", "backspace", "delete", "esc",
            "up", "down", "left", "right", "home", "end", "pageup", "pagedown",
            "f1", "f5", "f12",
            "a", "z", "0", "9",
            "-", "=", "[", "]", ";", "'", "/",
        ]
        for key in test_keys:
            code = _resolve_key_scancode(key)
            self.assertIsNotNone(code, f"Failed to resolve key: {key}")
            self.assertIsInstance(code, int)
            self.assertGreater(code, 0)

    def test_button_code_resolution(self) -> None:
        """Verify button names resolve to expected evdev scancodes and xdotool IDs."""
        btn_tests = [
            ("left", "1"),
            ("right", "3"),
            ("middle", "2"),
            ("side", "8"),
            ("extra", "9"),
        ]
        for name, expected_xdotool_str in btn_tests:
            code, xstr = _resolve_button_code(name)
            self.assertEqual(xstr, expected_xdotool_str)
            self.assertIsInstance(code, int)
            self.assertGreater(code, 0)

    def test_mouse_move_and_tracking(self) -> None:
        """Test coordinate dispatch and cursor tracking update."""
        mouse_move(350, 450, notify=False)
        from extra.core.platform.linux.geometry import get_cursor_position
        # Even if headless, internal tracking or xdotool returns valid integer tuple
        cx, cy = get_cursor_position()
        self.assertIsInstance(cx, int)
        self.assertIsInstance(cy, int)

    def test_smooth_mouse_move_bezier_and_windmouse(self) -> None:
        """Test biomechanical path dispatch with bezier and windmouse styles."""
        # Short distance
        smooth_mouse_move(360, 460, speed="fast", style="bezier", notify=False)
        # Medium distance
        smooth_mouse_move(420, 500, speed="fast", style="windmouse", notify=False)

    def test_mouse_clicks_and_buttons(self) -> None:
        """Test click, double click, down and up execution."""
        mouse_down("left")
        mouse_up("left")
        mouse_click(clicks=1, button="left")
        mouse_double_click()

    def test_mouse_drag_and_stroke(self) -> None:
        """Test drag and multi-point stroke dispatch with timing."""
        mouse_drag(200, 200, 250, 250, duration=0.05, steps=5)
        waypoints = [(300, 300), (320, 310), (340, 330), (360, 350)]
        mouse_stroke(waypoints, button="left", duration=0.1, smooth=True)

    def test_mouse_scroll(self) -> None:
        """Test vertical and horizontal mouse scrolling."""
        mouse_scroll(delta=120, horizontal=False)
        mouse_scroll(delta=-120, horizontal=False)
        mouse_scroll(delta=120, horizontal=True)

    def test_terminal_discrimination(self) -> None:
        """Verify terminal discrimination function returns boolean."""
        res = is_active_window_terminal()
        self.assertIsInstance(res, bool)

    def test_instant_type_and_hotkey(self) -> None:
        """Test keystroke sequence and hotkey dispatch."""
        send_hotkey(["shift"])
        instant_type("abc", press_enter=False)

    def test_atomic_clipboard_paste_mock(self) -> None:
        """Verify atomic clipboard paste pipeline handles text input safely."""
        # Test without throwing unexpected exceptions
        try:
            atomic_clipboard_paste("extra_unit_test_payload", restore_delay=0.01)
        except Exception as e:
            self.fail(f"atomic_clipboard_paste raised unexpected exception: {e}")

    def test_execute_batch_actions_standard(self) -> None:
        """Test compound hardware action batch execution."""
        batch = [
            {"action": "move", "x": 150, "y": 150},
            {"action": "sleep", "ms": 10},
            {"action": "hotkey", "keys": ["shift"]},
            {"action": "click", "button": "left", "clicks": 1},
        ]
        res = execute_batch_actions(batch, auto_settle=False)
        self.assertTrue(res["success"])
        self.assertEqual(res["executed_count"], 4)
        self.assertGreater(res["total_duration_ms"], 0.0)
        self.assertEqual(len(res["actions"]), 4)

    def test_execute_batch_actions_soul_conditions(self) -> None:
        """Test SOUL reflex condition branches within batch execution."""
        batch = [
            {
                "action": "eval",
                "condition": "desktop screen is visible",
                "then": [{"action": "sleep", "ms": 10}],
                "else": [{"action": "sleep", "ms": 5}],
            },
            {
                "action": "assert",
                "condition": "desktop session is responsive",
                "on_fail": "continue",
                "max_retries": 0,
            },
            {
                "action": "wait_for_state",
                "condition": "system is ready",
                "timeout_ms": 100,
                "poll_interval_ms": 20,
            },
        ]
        res = execute_batch_actions(batch, auto_settle=False)
        self.assertTrue(res["success"])
        # 4 actions: eval + executed then-branch sleep + assert + wait_for_state
        self.assertEqual(res["executed_count"], 4)


if __name__ == "__main__":
    unittest.main()
