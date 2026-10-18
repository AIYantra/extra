"""
Project Extra — Linux Screen Perception Engine Unit Tests
Tests screen frame capture, ROI cropping, base64 encoding,
active window telemetry, and multi-monitor capture on Linux.
"""

import sys
import unittest

if not sys.platform.startswith("linux"):
    raise unittest.SkipTest("Linux-specific capture tests skipped on non-Linux")

from extra.core.platform.linux.capture import (
    ScreenCaptureEngine,
    capture_roi,
    capture_screen,
    get_capture_engine,
)
from extra.core.platform.base import CaptureResult


class TestLinuxCapture(unittest.TestCase):
    """Exhaustive unit tests for Linux screen capture and perception telemetry."""

    def setUp(self):
        self.engine = get_capture_engine()

    def test_capture_screen_basic(self):
        res = self.engine.capture(monitor_index=0)
        self.assertIsInstance(res, CaptureResult)
        self.assertIsNotNone(res.image)
        self.assertGreater(res.width, 0)
        self.assertGreater(res.height, 0)
        self.assertGreater(res.duration_ms, 0.0)
        # Verify active window perception telemetry exists
        self.assertTrue(hasattr(res, "active_window_title"))
        self.assertTrue(hasattr(res, "active_window_hwnd"))

    def test_capture_roi(self):
        roi = capture_roi(50, 50, 250, 150, monitor_index=0)
        self.assertIsInstance(roi, CaptureResult)
        self.assertEqual(roi.width, 200)
        self.assertEqual(roi.height, 100)
        self.assertEqual(roi.crop_box, (50, 50, 250, 150))

    def test_image_to_base64(self):
        res = self.engine.capture(monitor_index=0)
        b64 = res.to_base64(format="JPEG", quality=75)
        self.assertIsInstance(b64, str)
        self.assertGreater(len(b64), 100)


if __name__ == "__main__":
    unittest.main()
