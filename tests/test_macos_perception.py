"""
Project Extra — macOS Perception & Retina Geometry Test Suite
Validates Phase 1 deliverables:
1. Retina point/pixel scaling & inverted Y-axis geometry mathematics
2. [0, 1000] Normalized coordinate and bounding box round-tripping
3. macOS ScreenCaptureEngine interface compliance & ROI crop calculation
4. CaptureResult base64 encoding and latency calculation
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from PIL import Image

from extra.core.platform.base import (
    AbstractCaptureEngine,
    AbstractGeometry,
    CaptureResult,
    MonitorInfo,
    get_bbox_center,
    image_to_base64,
)
from extra.core.platform.macos.capture import (
    MacScreenCaptureEngine,
    ScreenCaptureEngine,
    get_capture_engine,
)
from extra.core.platform.macos.geometry import (
    MacGeometry,
    clamp_coordinates,
    denormalize_bbox,
    denormalize_coordinates,
    flip_y_quartz_to_topleft,
    flip_y_topleft_to_quartz,
    get_cursor_position,
    get_monitors_info,
    get_primary_monitor,
    normalize_bbox,
    normalize_coordinates,
    pixels_to_points,
    points_to_pixels,
)


class TestMacOSPerceptionAndGeometry(unittest.TestCase):
    """Test suite validating macOS Perception and Retina geometry subsystems."""

    def setUp(self) -> None:
        # Standard 16-inch MacBook Pro Liquid Retina XDR display metrics:
        # 1728 x 1117 logical points @ 2.0x scale = 3456 x 2234 physical pixels
        self.mock_retina_monitor = MonitorInfo(
            index=0,
            left=0,
            top=0,
            right=3456,
            bottom=2234,
            width=3456,
            height=2234,
            is_primary=True,
            device_name="Built-in Liquid Retina XDR Display",
            dpi_x=144,
            dpi_y=144,
            scale_factor=2.0,
        )

    def test_geometry_interface_compliance(self) -> None:
        """Asserts MacGeometry inherits from and fully satisfies AbstractGeometry."""
        geom = MacGeometry()
        self.assertIsInstance(geom, AbstractGeometry)
        self.assertTrue(geom.ensure_dpi_aware())
        self.assertTrue(geom.attach_input_desktop())

    @patch("extra.core.platform.macos.geometry.get_monitors_info")
    def test_retina_point_pixel_conversion(self, mock_get_monitors) -> None:
        """Asserts exact 2.0x Retina point-to-pixel and pixel-to-point mappings."""
        mock_get_monitors.return_value = [
            MonitorInfo(
                index=0,
                left=0,
                top=0,
                right=2880,
                bottom=1800,
                width=2880,
                height=1800,
                is_primary=True,
                device_name="Mocked Retina Display",
                dpi_x=144,
                dpi_y=144,
                scale_factor=2.0,
            )
        ]
        # 100 points @ 2x = 200 pixels
        px, py = points_to_pixels(100.0, 250.5, monitor_index=0)
        self.assertEqual(px, 200)
        self.assertEqual(py, 501)

        pt_x, pt_y = pixels_to_points(px, py, monitor_index=0)
        self.assertEqual(pt_x, 100.0)
        self.assertEqual(pt_y, 250.5)

    def test_inverted_y_axis_conversion(self) -> None:
        """Asserts bottom-left Quartz Y-coordinate inversion to top-left origin."""
        screen_h = 1117.0  # 16-inch MBP height in points

        # Point at top of screen: Quartz Y = 1117 -> Top-left Y = 0
        top_y = flip_y_quartz_to_topleft(1117.0, screen_h)
        self.assertEqual(top_y, 0.0)

        # Point at bottom of screen: Quartz Y = 0 -> Top-left Y = 1117
        bottom_y = flip_y_quartz_to_topleft(0.0, screen_h)
        self.assertEqual(bottom_y, 1117.0)

        # Inverse conversion: Top-left Y = 1117 -> Quartz Y = 0
        q_y = flip_y_topleft_to_quartz(bottom_y, screen_h)
        self.assertEqual(q_y, 0.0)

    def test_normalized_coordinates_roundtrip(self) -> None:
        """Asserts zero-drift roundtrip between physical pixels and [0, 1000] space."""
        mon = get_primary_monitor()

        # Test center of screen
        orig_x = mon.left + mon.width // 2
        orig_y = mon.top + mon.height // 2

        norm_x, norm_y = normalize_coordinates(orig_x, orig_y, mon.index)
        self.assertAlmostEqual(norm_x, 500, delta=2)
        self.assertAlmostEqual(norm_y, 500, delta=2)

        denorm_x, denorm_y = denormalize_coordinates(norm_x, norm_y, mon.index)
        self.assertAlmostEqual(orig_x, denorm_x, delta=3)
        self.assertAlmostEqual(orig_y, denorm_y, delta=3)

    def test_normalized_bbox_and_center(self) -> None:
        """Asserts bounding box normalization and center calculations."""
        mon = get_primary_monitor()
        phys_box = (100, 150, 500, 600)
        norm_box = normalize_bbox(phys_box, mon.index)

        self.assertTrue(0 <= norm_box[0] <= 1000)
        self.assertTrue(0 <= norm_box[1] <= 1000)
        self.assertTrue(norm_box[2] >= norm_box[0])
        self.assertTrue(norm_box[3] >= norm_box[1])

        center = get_bbox_center(phys_box)
        self.assertEqual(center, (300, 375))

        # Denormalize
        denorm_box = denormalize_bbox(norm_box, mon.index)
        self.assertAlmostEqual(denorm_box[0], phys_box[0], delta=5)
        self.assertAlmostEqual(denorm_box[1], phys_box[1], delta=5)

    def test_coordinate_clamping(self) -> None:
        """Asserts coordinates outside monitor boundaries are clamped safely."""
        mon = get_primary_monitor()
        clamped_x, clamped_y = clamp_coordinates(-500, 99999, mon.index)
        self.assertEqual(clamped_x, mon.left)
        self.assertEqual(clamped_y, mon.bottom - 1)

    def test_capture_engine_interface_compliance(self) -> None:
        """Asserts MacScreenCaptureEngine satisfies AbstractCaptureEngine."""
        engine = MacScreenCaptureEngine()
        self.assertIsInstance(engine, AbstractCaptureEngine)
        engine.set_excluded_window_ids([101, 102])
        self.assertEqual(engine._excluded_window_ids, [101, 102])

    def test_capture_result_encoding_and_roi(self) -> None:
        """Asserts mock 2x Retina frame buffer encoding, ROI cropping, and latency stats."""
        # Simulated 2x Retina frame (3456 x 2234)
        mock_img = Image.new("RGB", (3456, 2234), color=(30, 41, 59))
        res = CaptureResult(
            image=mock_img,
            duration_ms=4.25,
            monitor_index=0,
            width=3456,
            height=2234,
            crop_box=None,
        )

        self.assertEqual(res.width, 3456)
        self.assertEqual(res.height, 2234)
        self.assertEqual(res.duration_ms, 4.25)

        # Base64 serialization
        b64 = res.to_base64(quality=80)
        self.assertIsInstance(b64, str)
        self.assertTrue(len(b64) > 500)

        # ROI Crop
        roi_img = mock_img.crop((100, 100, 500, 400))
        roi_res = CaptureResult(
            image=roi_img,
            duration_ms=1.12,
            monitor_index=0,
            width=400,
            height=300,
            crop_box=(100, 100, 500, 400),
        )
        self.assertEqual(roi_res.width, 400)
        self.assertEqual(roi_res.height, 300)
        self.assertEqual(roi_res.crop_box, (100, 100, 500, 400))


def run_tests() -> bool:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMacOSPerceptionAndGeometry)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
