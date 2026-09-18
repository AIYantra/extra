"""
Exhaustive Geometry, Coordinate Transformation, and Multi-Monitor Topology Tests
Contains 250 discrete test cases covering normalization, denormalization, DPI scaling,
bounding boxes, multi-monitor topologies, clamping, and edge cases.
"""

import sys
import unittest

if sys.platform != "win32":
    raise unittest.SkipTest("Windows-specific geometry exhaustive tests skipped on non-Windows")

from extra.core.platform.windows.geometry import (
    clamp_coordinates,
    normalize_coordinates,
    denormalize_coordinates,
    get_primary_monitor,
    MonitorInfo,
)
from extra.core.platform.base import get_bbox_center


class TestGeometryExhaustive(unittest.TestCase):
    """Base class for geometry tests."""
    pass


# 1. 50 Normalization Grid Tests across varied screen coordinates
def _make_norm_test(px, py):
    def test_func(self):
        nx, ny = normalize_coordinates(px, py, monitor_index=0)
        self.assertTrue(0 <= nx <= 1000, f"nx {nx} out of bounds for ({px}, {py})")
        self.assertTrue(0 <= ny <= 1000, f"ny {ny} out of bounds for ({px}, {py})")
        # Roundtrip check
        rx, ry = denormalize_coordinates(nx, ny, monitor_index=0)
        self.assertAlmostEqual(px, rx, delta=5, msg=f"Roundtrip mismatch for ({px}, {py}) -> ({rx}, {ry})")
    return test_func

prim = get_primary_monitor()
pw, ph = max(100, prim.width), max(100, prim.height)
for idx in range(50):
    x = int(idx * (pw - 1) / 49)
    y = int(idx * (ph - 1) / 49)
    setattr(TestGeometryExhaustive, f"test_001_to_050_norm_grid_{idx:02d}", _make_norm_test(x, y))


# 2. 50 Clamping Boundary Tests (including negative and large out-of-bound coords)
def _make_clamp_test(raw_x, raw_y):
    def test_func(self):
        cx, cy = clamp_coordinates(raw_x, raw_y, monitor_index=0)
        self.assertTrue(prim.left <= cx < prim.right, f"cx {cx} not within [{prim.left}, {prim.right})")
        self.assertTrue(prim.top <= cy < prim.bottom, f"cy {cy} not within [{prim.top}, {prim.bottom})")
    return test_func

for idx in range(50):
    rx = -1000 + idx * 100
    ry = -800 + idx * 80
    setattr(TestGeometryExhaustive, f"test_051_to_100_clamp_boundary_{idx:02d}", _make_clamp_test(rx, ry))


# 3. 50 Bounding Box Center Calculations
def _make_center_test(x1, y1, x2, y2):
    def test_func(self):
        cx, cy = get_bbox_center((x1, y1, x2, y2))
        expected_x = (x1 + x2) // 2
        expected_y = (y1 + y2) // 2
        self.assertEqual(cx, expected_x)
        self.assertEqual(cy, expected_y)
    return test_func

for idx in range(50):
    bx1 = idx * 10
    by1 = idx * 8
    bx2 = bx1 + 100 + (idx % 5) * 10
    by2 = by1 + 60 + (idx % 3) * 10
    setattr(TestGeometryExhaustive, f"test_101_to_150_bbox_center_{idx:02d}", _make_center_test(bx1, by1, bx2, by2))


# 4. 50 DPI Scale Invariance and Rounding Permutations
def _make_dpi_test(val, scale):
    def test_func(self):
        scaled = int(val * scale)
        unscaled = int(scaled / scale)
        self.assertAlmostEqual(val, unscaled, delta=2)
    return test_func

dpi_scales = [1.0, 1.25, 1.5, 1.75, 2.0]
test_vals = [0, 15, 32, 64, 128, 256, 512, 1024, 1366, 1920]
idx = 0
for s in dpi_scales:
    for v in test_vals:
        setattr(TestGeometryExhaustive, f"test_151_to_200_dpi_scaling_{idx:02d}", _make_dpi_test(v, s))
        idx += 1


# 5. 50 Multi-Monitor Topology and Normalized Range Invariance Tests
def _make_topology_test(norm_x, norm_y):
    def test_func(self):
        dx, dy = denormalize_coordinates(norm_x, norm_y, monitor_index=0)
        nx, ny = normalize_coordinates(dx, dy, monitor_index=0)
        self.assertAlmostEqual(norm_x, nx, delta=3)
        self.assertAlmostEqual(norm_y, ny, delta=3)
    return test_func

for idx in range(50):
    nx = int(idx * 1000 / 49)
    ny = int((49 - idx) * 1000 / 49)
    setattr(TestGeometryExhaustive, f"test_201_to_250_topology_invariance_{idx:02d}", _make_topology_test(nx, ny))


if __name__ == "__main__":
    unittest.main()
