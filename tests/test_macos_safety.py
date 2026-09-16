"""
Unit tests for Project Extra — macOS Closed-Loop Resilience & Safety Gates
Tests perceptual hash diffing, 2-strike loop breaker, corner abort, and macOS Cmd+Opt+Shift+Q killswitch.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import numpy as np
from PIL import Image

from extra.core.stall_breaker import EmergencyAbortError, StallBreaker, StallStatus


class TestMacOSSafetyGates(unittest.TestCase):
    """Tests for emergency corner fail-safe and macOS global hotkey trap."""

    def setUp(self):
        self.breaker = StallBreaker(max_strikes=2, corner_abort_pixels=3)

    @patch("extra.core.stall_breaker.get_cursor_position")
    def test_corner_failsafe_triggered(self, mock_cursor):
        mock_cursor.return_value = (1, 2)
        with self.assertRaises(EmergencyAbortError) as ctx:
            self.breaker.check_safety_abort()
        self.assertIn("emergency abort corner", str(ctx.exception))

    @patch("extra.core.stall_breaker.get_cursor_position")
    def test_corner_failsafe_normal(self, mock_cursor):
        mock_cursor.return_value = (500, 400)
        # Should not raise
        self.breaker.check_safety_abort()

    @patch("extra.core.stall_breaker.sys")
    @patch("extra.core.stall_breaker.CG")
    @patch("extra.core.stall_breaker.get_cursor_position")
    def test_macos_emergency_hotkey_triggered(self, mock_cursor, mock_cg, mock_sys):
        mock_cursor.return_value = (500, 400)
        mock_sys.platform = "darwin"

        mock_cg.kCGEventSourceStateCombinedSessionState = 0
        mock_cg.kCGEventFlagMaskCommand = 0x00100000
        mock_cg.kCGEventFlagMaskAlternate = 0x00080000
        mock_cg.kCGEventFlagMaskShift = 0x00020000

        # Cmd + Opt + Shift active
        mock_cg.CGEventSourceFlagsState.return_value = (
            mock_cg.kCGEventFlagMaskCommand
            | mock_cg.kCGEventFlagMaskAlternate
            | mock_cg.kCGEventFlagMaskShift
        )
        # 'q' key down (key 12)
        mock_cg.CGEventSourceKeyState.return_value = True

        with self.assertRaises(EmergencyAbortError) as ctx:
            self.breaker.check_safety_abort()
        self.assertIn("Cmd+Opt+Shift+Q", str(ctx.exception))

    @patch("extra.core.stall_breaker.sys")
    @patch("extra.core.stall_breaker.CG")
    @patch("extra.core.stall_breaker.get_cursor_position")
    def test_macos_emergency_hotkey_not_triggered_partial_modifiers(
        self, mock_cursor, mock_cg, mock_sys
    ):
        mock_cursor.return_value = (500, 400)
        mock_sys.platform = "darwin"

        mock_cg.kCGEventSourceStateCombinedSessionState = 0
        mock_cg.kCGEventFlagMaskCommand = 0x00100000
        mock_cg.kCGEventFlagMaskAlternate = 0x00080000
        mock_cg.kCGEventFlagMaskShift = 0x00020000

        # Only Cmd pressed, no Opt or Shift
        mock_cg.CGEventSourceFlagsState.return_value = mock_cg.kCGEventFlagMaskCommand
        mock_cg.CGEventSourceKeyState.return_value = True

        # Should not raise
        self.breaker.check_safety_abort()

    @patch("extra.core.stall_breaker.get_cursor_position")
    def test_two_strike_loop_breaker(self, mock_cursor):
        mock_cursor.return_value = (500, 400)

        # 2 identical images
        img1 = Image.new("RGB", (100, 100), color=(255, 0, 0))
        img2 = Image.new("RGB", (100, 100), color=(255, 0, 0))

        # Strike 1: Warning
        out1 = self.breaker.evaluate_action(img1, img2, action_name="click")
        self.assertEqual(out1.status, StallStatus.WARNING)
        self.assertEqual(out1.strikes, 1)

        # Strike 2: Stalled
        out2 = self.breaker.evaluate_action(img1, img2, action_name="click")
        self.assertEqual(out2.status, StallStatus.STALLED)
        self.assertEqual(out2.strikes, 2)

        # Visual change: Reset to normal
        img3 = Image.new("RGB", (100, 100), color=(0, 255, 0))
        out3 = self.breaker.evaluate_action(img2, img3, action_name="type")
        self.assertEqual(out3.status, StallStatus.NORMAL)
        self.assertEqual(out3.strikes, 0)


if __name__ == "__main__":
    unittest.main()
