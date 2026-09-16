"""
Project Extra — Regression Test Suite for Issue #4
Desktop Automation Bottlenecks reported by @harshbuttru3:
1. extra_screenshot file persistence & payload truncation prevention.
2. StallBreaker remote / global visual delta fallback (preventing false-stalls in 3D viewports/canvas).
3. extra_focus_window retry polling with configurable timeout.
4. resolve_executable discovery of MSIX/Microsoft Store apps and Blender installations.
"""

import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from PIL import Image

from extra.core.platform.base import CaptureResult
from extra.core.stall_breaker import StallBreaker, StallStatus
from extra.mcp.server import extra_screenshot, extra_focus_window

if sys.platform == "win32":
    from extra.core.platform.windows.shell import resolve_executable, APP_REGISTRY
    from extra.core.platform.windows.focus import find_window_by_title
else:
    from extra.core.platform.macos.shell import resolve_executable, MAC_APP_REGISTRY as APP_REGISTRY
    from extra.core.platform.macos.focus import find_window_by_title


class TestIssue4Bottlenecks(unittest.TestCase):
    """Verifies all 4 operational friction point fixes reported in Issue #4 (credit: @harshbuttru3)."""

    @patch("extra.mcp.server.capture_screen")
    def test_screenshot_file_persistence_and_base64_flag(self, mock_capture):
        """extra_screenshot must write to disk and omit heavy base64 strings by default to prevent LLM truncation."""
        test_img = Image.new("RGB", (200, 150), color=(80, 120, 200))
        mock_capture.return_value = CaptureResult(
            image=test_img,
            duration_ms=12.5,
            monitor_index=0,
            width=200,
            height=150,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = os.path.join(tmpdir, "test_shot.png")

            # Default behavior: saves to file, omits giant base64 payload
            res = extra_screenshot(save_to_file=True, file_path=custom_path, include_base64=False)
            self.assertIn("file_path", res)
            self.assertEqual(res["file_path"].replace("\\", "/"), custom_path.replace("\\", "/"))
            self.assertTrue(os.path.exists(custom_path))
            self.assertNotIn("screenshot_base64", res)

            # Explicit include_base64=True
            res_b64 = extra_screenshot(save_to_file=False, include_base64=True)
            self.assertIn("screenshot_base64", res_b64)
            self.assertIsInstance(res_b64["screenshot_base64"], str)
            self.assertGreater(len(res_b64["screenshot_base64"]), 100)

    def test_stall_breaker_remote_visual_fallback(self):
        """StallBreaker must detect distant screen changes when local ROI shows zero delta."""
        breaker = StallBreaker(max_strikes=2)

        # 1. Local ROI images are identical (simulating clicking a static toolbar button)
        roi_before = Image.new("RGB", (200, 200), color=(50, 50, 50))
        roi_after = Image.new("RGB", (200, 200), color=(50, 50, 50))

        # 2. Remote screen changes (simulating 3D viewport updating elsewhere on monitor)
        full_before = Image.new("RGB", (1920, 1080), color=(30, 30, 30))
        full_after = full_before.copy()
        # Draw a white patch in the viewport area
        for x in range(500, 900):
            for y in range(300, 700):
                full_after.putpixel((x, y), (240, 240, 240))

        outcome = breaker.evaluate_action(
            roi_before,
            roi_after,
            action_name="click_toolbar_button",
            before_full_image=full_before,
            after_full_image=full_after,
        )

        # Must NOT stall; strikes must remain 0 due to global fallback
        self.assertEqual(outcome.status, StallStatus.NORMAL)
        self.assertEqual(outcome.strikes, 0)
        self.assertIn("remote visual change", outcome.message)

        # 3. Verify that if BOTH local ROI and full screen are unchanged, strikes increment normally
        stalled_outcome_1 = breaker.evaluate_action(
            roi_before,
            roi_after,
            action_name="click_dead_button",
            before_full_image=full_before,
            after_full_image=full_before,
        )
        self.assertEqual(stalled_outcome_1.status, StallStatus.WARNING)
        self.assertEqual(stalled_outcome_1.strikes, 1)

        stalled_outcome_2 = breaker.evaluate_action(
            roi_before,
            roi_after,
            action_name="click_dead_button",
            before_full_image=full_before,
            after_full_image=full_before,
        )
        self.assertEqual(stalled_outcome_2.status, StallStatus.STALLED)
        self.assertEqual(stalled_outcome_2.strikes, 2)

    def test_focus_window_polling_timeout(self):
        """extra_focus_window and find_window_by_title must poll for the specified timeout before failing."""
        t0 = time.perf_counter()
        res = extra_focus_window(window_title="NonExistentWindow_Issue4_Test_12345", timeout=0.2)
        duration = time.perf_counter() - t0

        self.assertFalse(res["success"])
        self.assertIn("timed out", res["error"])
        self.assertGreaterEqual(duration, 0.15)

    def test_resolve_executable_registry_and_store_paths(self):
        """resolve_executable must recognize 'blender' and search Store execution aliases on Windows."""
        if sys.platform != "win32":
            self.skipTest("Windows-specific executable resolution test")

        self.assertIn("blender", APP_REGISTRY)
        self.assertEqual(APP_REGISTRY["blender"]["target"], "blender.exe")

        # Resolving calculator should work
        calc_path = resolve_executable("calc")
        self.assertTrue(calc_path is not None)

        # Resolving blender should return blender.exe, Store alias, or Program Files path
        blender_res = resolve_executable("blender")
        self.assertTrue(blender_res is not None)
        self.assertTrue("blender" in blender_res.lower())


if __name__ == "__main__":
    unittest.main()
