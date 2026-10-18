"""
Project Extra — Linux Platform Geometry & Normalization Unit Tests
Tests monitor discovery, coordinate normalization, denormalization,
clamping, and multi-monitor boundaries on Linux.
"""

import sys
import unittest

if not sys.platform.startswith("linux"):
    raise unittest.SkipTest("Linux-specific geometry tests skipped on non-Linux")

from extra.core.platform.linux.geometry import (
    clamp_coordinates,
    denormalize_bbox,
    denormalize_coordinates,
    ensure_dpi_aware,
    get_cursor_position,
    get_monitors_info,
    get_primary_monitor,
    get_virtual_screen_bounds,
    normalize_bbox,
    normalize_coordinates,
    LinuxGeometry,
)
from extra.core.platform.base import get_bbox_center


class TestLinuxGeometry(unittest.TestCase):
    """Exhaustive unit tests for Linux geometry normalization and metrics."""

    def setUp(self):
        self.geo = LinuxGeometry()
        self.primary = get_primary_monitor()

    def test_dpi_and_attach(self):
        self.assertTrue(self.geo.ensure_dpi_aware())
        self.assertTrue(self.geo.attach_input_desktop())

    def test_monitor_discovery(self):
        monitors = self.geo.get_monitors_info()
        self.assertGreater(len(monitors), 0)
        prim = self.geo.get_primary_monitor()
        self.assertIsNotNone(prim)
        self.assertGreater(prim.width, 0)
        self.assertGreater(prim.height, 0)

    def test_virtual_screen_bounds(self):
        vx, vy, vw, vh = self.geo.get_virtual_screen_bounds()
        self.assertGreater(vw, 0)
        self.assertGreater(vh, 0)

    def test_cursor_position(self):
        cx, cy = self.geo.get_cursor_position()
        self.assertIsInstance(cx, int)
        self.assertIsInstance(cy, int)

    def test_coordinate_normalization_and_roundtrip(self):
        pw, ph = self.primary.width, self.primary.height
        # Test corners and center
        test_points = [(0, 0), (pw // 2, ph // 2), (pw - 1, ph - 1)]
        for px, py in test_points:
            nx, ny = self.geo.normalize_coordinates(px, py)
            self.assertTrue(0 <= nx <= 1000)
            self.assertTrue(0 <= ny <= 1000)
            rx, ry = self.geo.denormalize_coordinates(nx, ny)
            self.assertAlmostEqual(px, rx, delta=3)
            self.assertAlmostEqual(py, ry, delta=3)

    def test_clamping(self):
        pw, ph = self.primary.width, self.primary.height
        # Below 0
        cx, cy = self.geo.clamp_coordinates(-500, -200)
        self.assertEqual(cx, self.primary.left)
        self.assertEqual(cy, self.primary.top)
        # Above bounds
        cx2, cy2 = self.geo.clamp_coordinates(pw + 1000, ph + 500)
        self.assertEqual(cx2, self.primary.right - 1)
        self.assertEqual(cy2, self.primary.bottom - 1)

    def test_bbox_normalization(self):
        bbox = (100, 100, 500, 400)
        norm_b = self.geo.normalize_bbox(bbox)
        self.assertTrue(0 <= norm_b[0] <= 1000)
        self.assertTrue(0 <= norm_b[1] <= 1000)
        self.assertTrue(norm_b[2] >= norm_b[0])
        self.assertTrue(norm_b[3] >= norm_b[1])
        # Roundtrip
        denorm_b = self.geo.denormalize_bbox(norm_b)
        self.assertAlmostEqual(bbox[0], denorm_b[0], delta=4)
        self.assertAlmostEqual(bbox[1], denorm_b[1], delta=4)
        self.assertAlmostEqual(bbox[2], denorm_b[2], delta=4)
        self.assertAlmostEqual(bbox[3], denorm_b[3], delta=4)

    def test_bbox_center(self):
        center = get_bbox_center((100, 200, 300, 400))
        self.assertEqual(center, (200, 300))


if __name__ == "__main__":
    unittest.main()
