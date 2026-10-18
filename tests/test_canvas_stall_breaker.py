"""
Tests for Project Extra — Virtual Canvas Stall-Breaker & Universal Keyboard Navigation
Verifies spatial click loop detection, transient context menu stall prevention,
and intelligent keyboard fast-path recommendations for virtualized spreadsheet/canvas interfaces.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch
from PIL import Image

from extra.core.stall_breaker import (
    StallBreaker,
    StallStatus,
)


def _make_dummy_image(color=(255, 255, 255)):
    return Image.new("RGB", (200, 200), color=color)


class TestCanvasStallBreaker(unittest.TestCase):
    """Tests for spatial click loop detection and spreadsheet navigation remedies."""

    def setUp(self):
        self._cursor_patch = patch("extra.core.stall_breaker.get_cursor_position", return_value=(500, 500))
        self._cursor_patch.start()

    def tearDown(self):
        self._cursor_patch.stop()

    def test_spatial_canvas_loop_detected_on_sheets(self):
        sb = StallBreaker(max_strikes=2)
        img_before = _make_dummy_image()
        img_after = _make_dummy_image()  # Zero visual delta

        # Click 1 at tab bar coordinate (181, 711)
        outcome1 = sb.evaluate_action(
            img_before,
            img_after,
            action_name="click_181_711",
            click_coords=(181, 711),
            window_title="Aurora Launch Control Center - Google Sheets - Google Chrome",
        )
        self.assertEqual(outcome1.status, StallStatus.WARNING)
        self.assertEqual(outcome1.strikes, 1)

        # Click 2 at nearby coordinate (185, 715) with zero change (would normally reset strike to 1)
        outcome2 = sb.evaluate_action(
            img_before,
            img_after,
            action_name="click_185_715",
            click_coords=(185, 715),
            window_title="Aurora Launch Control Center - Google Sheets - Google Chrome",
        )
        self.assertEqual(outcome2.status, StallStatus.WARNING)

        # Click 3 at nearby coordinate (180, 710) - triggers spatial loop breaker!
        outcome3 = sb.evaluate_action(
            img_before,
            img_after,
            action_name="click_180_710",
            click_coords=(180, 710),
            window_title="Aurora Launch Control Center - Google Sheets - Google Chrome",
        )
        self.assertEqual(outcome3.status, StallStatus.STALLED)
        self.assertEqual(outcome3.cognitive_state, "CANVAS_LOOP")
        self.assertIn("VIRTUAL CANVAS LOOP DETECTED", outcome3.message)
        self.assertIn("Shift + F11", outcome3.recommended_action)
        self.assertIn("Alt + /", outcome3.recommended_action)

    def test_spatial_loop_cleared_on_state_change(self):
        sb = StallBreaker(max_strikes=2)
        img1 = _make_dummy_image((255, 255, 255))
        img2 = _make_dummy_image((255, 255, 255))
        img_changed = _make_dummy_image((0, 0, 0))  # Significant visual delta

        # 2 failed clicks
        sb.evaluate_action(img1, img2, click_coords=(100, 100))
        sb.evaluate_action(img1, img2, click_coords=(102, 101))
        self.assertEqual(len(sb._recent_clicks), 2)

        # 3rd click causes visual change
        outcome = sb.evaluate_action(img1, img_changed, click_coords=(100, 100))
        self.assertEqual(outcome.status, StallStatus.NORMAL)
        self.assertEqual(len(sb._recent_clicks), 0)
        self.assertEqual(sb.current_strikes, 0)

    def test_distant_clicks_do_not_trigger_spatial_loop(self):
        sb = StallBreaker(max_strikes=2)
        img1 = _make_dummy_image()
        img2 = _make_dummy_image()

        # Clicks far apart (> 45px distance)
        sb.evaluate_action(img1, img2, click_coords=(50, 50))
        sb.evaluate_action(img1, img2, click_coords=(300, 300))
        outcome = sb.evaluate_action(img1, img2, click_coords=(800, 600))

        self.assertNotEqual(outcome.cognitive_state, "CANVAS_LOOP")


if __name__ == "__main__":
    unittest.main()
