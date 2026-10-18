"""
Tests for Project Extra — Bridge Perception Sandbox & Native Crop Support
Verifies that extra_execute_bridge cannot be subverted for screen-scraping loops,
and confirms zero-hop perception notices in extra_screenshot.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from extra.fastpath.bridge import (
    check_bridge_payload_safety,
    execute_bridge,
)
from extra.mcp.server import extra_screenshot


class TestBridgeSandbox(unittest.TestCase):
    """Tests for execution bridge security boundaries and zero-hop perception."""

    def test_bridge_detects_prohibited_mss_import(self):
        payload = """
        from PIL import Image
        import mss
        with mss.mss() as sct:
            img = sct.grab({"top": 670, "left": 0, "width": 450, "height": 60})
        """
        error = check_bridge_payload_safety(payload, runtime="python")
        self.assertIsNotNone(error)
        self.assertIn("BRIDGE ARCHITECTURE VIOLATION", error)
        self.assertIn("mss", error)

    def test_bridge_detects_prohibited_imagegrab(self):
        payload = "from PIL import ImageGrab\nim = ImageGrab.grab()"
        error = check_bridge_payload_safety(payload, runtime="python")
        self.assertIsNotNone(error)
        self.assertIn("ImageGrab", error)

    def test_bridge_detects_prohibited_getdc(self):
        payload = "import win32gui\nhdc = win32gui.GetDC(0)"
        error = check_bridge_payload_safety(payload, runtime="python")
        self.assertIsNotNone(error)
        self.assertIn("GetDC", error)

    def test_bridge_allows_legitimate_image_drawing(self):
        # Creating graphics from scratch via PIL is 100% allowed
        payload = """
        from PIL import Image, ImageDraw
        img = Image.new("RGBA", (400, 300), (0, 0, 0, 255))
        draw = ImageDraw.Draw(img)
        draw.rectangle([10, 10, 100, 100], fill="cyan")
        """
        error = check_bridge_payload_safety(payload, runtime="python")
        self.assertIsNone(error)

    def test_bridge_blocks_execution_of_screen_capture_payload(self):
        payload = "import mss\nsct = mss.mss()"
        result = execute_bridge(runtime="python", payload=payload)

        self.assertFalse(result.success)
        self.assertEqual(result.returncode, -4)
        self.assertIn("BRIDGE ARCHITECTURE VIOLATION", result.error)
        self.assertTrue(result.metadata.get("security_blocked"))

    def test_bridge_executes_legitimate_computation(self):
        payload = "print('COMPUTATION_RESULT=' + str(245 * 12))"
        result = execute_bridge(runtime="python", payload=payload)

        self.assertTrue(result.success)
        self.assertEqual(result.returncode, 0)
        self.assertIn("COMPUTATION_RESULT=2940", result.stdout)

    def test_extra_screenshot_includes_zero_hop_perception_notice(self):
        with patch("extra.mcp.server.capture_screen") as mock_cap, \
             patch("extra.mcp.server.distill_screen") as mock_distill:
            mock_frame = MagicMock()
            mock_frame.width = 1920
            mock_frame.height = 1080
            mock_frame.duration_ms = 15.0
            mock_frame.image = MagicMock()
            mock_cap.return_value = mock_frame

            mock_dist_res = MagicMock()
            mock_dist_res.content = "Window: Calculator"
            mock_dist_res.element_count = 5
            mock_dist_res.interactive_count = 3
            mock_distill.return_value = mock_dist_res

            res = extra_screenshot(crop_box=[100, 200, 500, 600], save_to_file=False)

            self.assertEqual(res["crop_box"], [100, 200, 500, 600])
            self.assertIn("perception_notice", res)
            self.assertIn("Zero-Hop Protocol Active", res["perception_notice"])
            self.assertIn("DO NOT call view_file", res["perception_notice"])


if __name__ == "__main__":
    unittest.main()
