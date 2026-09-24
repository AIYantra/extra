"""
Unit & Integration Test Suite — Project SOUL Cognitive Stall Breaker
Validates spinner loop detection, modal trap diagnostics, and hung app detection.
Built using standard library unittest for zero external test runner dependency.
"""

import unittest
from unittest.mock import MagicMock, patch
from PIL import Image

from extra.core.stall_breaker import (
    ActionOutcome,
    StallBreaker,
    StallStatus,
)


class TestCognitiveStallBreaker(unittest.TestCase):
    """Tests SOUL-enhanced cognitive stall supervision."""

    def setUp(self):
        self.breaker = StallBreaker(hash_threshold=2, pixel_threshold=0.5, max_strikes=2)
        # Create dummy 100x100 RGB images
        self.img_black = Image.new("RGB", (100, 100), (0, 0, 0))
        self.img_white = Image.new("RGB", (100, 100), (255, 255, 255))
        # Small pixel delta image (simulating subtle spinner/cursor animation)
        self.img_subtle1 = Image.new("RGB", (100, 100), (0, 0, 0))
        self.img_subtle1.putpixel((50, 50), (255, 255, 255))
        self.img_subtle2 = Image.new("RGB", (100, 100), (0, 0, 0))
        self.img_subtle2.putpixel((51, 50), (255, 255, 255))

    def test_normal_visual_progression(self):
        """Major visible changes should evaluate to NORMAL and 0 strikes."""
        outcome = self.breaker.evaluate_action(
            before_image=self.img_black,
            after_image=self.img_white,
            action_name="load_page",
        )
        self.assertEqual(outcome.status, StallStatus.NORMAL)
        self.assertEqual(outcome.strikes, 0)
        self.assertFalse(outcome.is_spinner_detected)
        self.assertFalse(outcome.is_modal_blocked)

    def test_zero_change_two_strike_stall(self):
        """Zero visual delta accumulates strikes and flags STALLED on strike 2."""
        # Strike 1
        out1 = self.breaker.evaluate_action(
            before_image=self.img_black,
            after_image=self.img_black,
            action_name="click_button",
        )
        self.assertEqual(out1.status, StallStatus.WARNING)
        self.assertEqual(out1.strikes, 1)

        # Strike 2 -> STALLED
        out2 = self.breaker.evaluate_action(
            before_image=self.img_black,
            after_image=self.img_black,
            action_name="click_button",
        )
        self.assertEqual(out2.status, StallStatus.STALLED)
        self.assertEqual(out2.strikes, 2)
        self.assertIn("STALL DETECTED", out2.message)

    def test_modal_trap_detection(self):
        """When an action produces zero delta due to an active modal dialog, SOUL diagnoses the trap."""
        with patch.object(self.breaker, "classify_cognitive_state", return_value=("MODAL_BLOCKED", "Dismiss with Escape")):
            out = self.breaker.evaluate_action(
                before_image=self.img_black,
                after_image=self.img_black,
                before_hwnd=1001,
                after_hwnd=1001,
                action_name="click_canvas",
            )
            self.assertEqual(out.status, StallStatus.WARNING)
            self.assertEqual(out.strikes, 1)
            self.assertTrue(out.is_modal_blocked)
            self.assertEqual(out.cognitive_state, "MODAL_BLOCKED")
            self.assertIn("MODAL TRAP DETECTED", out.message)
            self.assertIn("Dismiss with Escape", out.message)

    def test_spinner_loop_breaker(self):
        """
        When consecutive turns produce subtle repeating diffs with spinner context,
        SOUL overrides the visual delta and accumulates strikes to break the spinner trap.
        """
        # Turn 1: Subtle animation
        self.breaker.evaluate_action(
            before_image=self.img_subtle1,
            after_image=self.img_subtle2,
            action_name="click_submit",
        )

        # Turn 2: Mock SOUL identifying active spinner loop
        with patch.object(self.breaker, "classify_cognitive_state", return_value=("SPINNER_BLOCKED", "Wait for completion or send Escape")):
            out = self.breaker.evaluate_action(
                before_image=self.img_subtle1,
                after_image=self.img_subtle2,
                action_name="click_submit",
            )
            # Even though pixels technically differed, SOUL treats it as non-progressing
            self.assertTrue(out.is_spinner_detected)
            self.assertEqual(out.cognitive_state, "SPINNER_BLOCKED")
            self.assertIn("SPINNER LOOP DETECTED", out.message)
            self.assertGreaterEqual(out.strikes, 1)

    def test_app_crashed_detection(self):
        """Hung window immediately triggers STALLED on strike 1."""
        with patch.object(self.breaker, "classify_cognitive_state", return_value=("APP_CRASHED", "Kill or restart process.")):
            out = self.breaker.evaluate_action(
                before_image=self.img_black,
                after_image=self.img_black,
                before_hwnd=9999,
                after_hwnd=9999,
                action_name="open_menu",
            )
            self.assertEqual(out.status, StallStatus.STALLED)
            self.assertEqual(out.cognitive_state, "APP_CRASHED")
            self.assertIn("APPLICATION CRASH DETECTED", out.message)

    def test_reset_clears_cognitive_state(self):
        """Calling reset() completely clears strikes and cognitive memory."""
        self.breaker._current_strikes = 2
        self.breaker._recent_diffs = [2, 3, 4]
        self.breaker._last_cognitive_state = "SPINNER_BLOCKED"

        self.breaker.reset()
        self.assertEqual(self.breaker.current_strikes, 0)
        self.assertEqual(len(self.breaker._recent_diffs), 0)
        self.assertEqual(self.breaker._last_cognitive_state, "NORMAL_PROGRESS")


if __name__ == "__main__":
    unittest.main()
