"""
Project Extra — Human-Like Mouse Trajectory & Stroke Engine Tests
Verifies mathematical correctness of Bézier arcs, WindMouse physics simulation,
Fitts's Law velocity profiler, Catmull-Rom splines, and MCP tool dispatch.
"""

import math
import unittest
from unittest.mock import patch
from typing import List, Tuple

from extra.core.motion import (
    apply_jitter,
    generate_bezier_path,
    generate_catmull_rom_spline,
    generate_stroke_path,
    generate_windmouse_path,
    FittsProfiler,
)
from extra.core.input_engine import (
    execute_batch_actions,
    mouse_move,
    mouse_stroke,
    smooth_mouse_move,
)
from extra.mcp.server import extra_mouse_move, extra_stroke


class TestHumanMotionEngine(unittest.TestCase):
    """Unit tests for the extra.core.motion mathematical components."""

    def test_bezier_endpoints_preserved(self):
        """Bézier curve must strictly start at start point and end at target point."""
        start = (100, 150)
        end = (600, 750)
        path = generate_bezier_path(start, end, steps=25)
        self.assertEqual(path[0], start)
        self.assertEqual(path[-1], end)
        self.assertEqual(len(path), 26)

    def test_bezier_curvature_non_linear(self):
        """Bézier trajectory must introduce realistic orthogonal deviation."""
        start = (0, 0)
        end = (1000, 0)
        path = generate_bezier_path(start, end, steps=30, deviation_factor=0.3)
        # Check that intermediate points have non-zero y deviations (orthogonal wander)
        y_deviations = [abs(p[1]) for p in path[5:-5]]
        self.assertTrue(any(y > 5 for y in y_deviations), "Expected non-zero curve deviation")

    def test_catmull_rom_passes_through_waypoints(self):
        """Catmull-Rom spline must pass through all specified waypoints."""
        waypoints = [(100, 200), (300, 450), (600, 150), (800, 500)]
        spline = generate_catmull_rom_spline(waypoints, steps_per_segment=15)
        self.assertEqual(spline[0], waypoints[0])
        self.assertEqual(spline[-1], waypoints[-1])
        self.assertGreater(len(spline), len(waypoints))

        # Check that middle waypoints are closely interpolated
        for wp in waypoints[1:-1]:
            min_dist = min(math.hypot(p[0] - wp[0], p[1] - wp[1]) for p in spline)
            self.assertLessEqual(min_dist, 5.0, f"Spline deviated too far from waypoint {wp}")

    def test_jitter_preserves_anchors(self):
        """Micro-jitter should perturb inner points while anchoring start and end."""
        path = [(x * 10, x * 10) for x in range(30)]
        jittered = apply_jitter(path, amplitude=2.0, frequency=1.0)
        self.assertEqual(jittered[0], path[0])
        self.assertEqual(jittered[-1], path[-1])
        self.assertEqual(len(jittered), len(path))

    def test_windmouse_convergence(self):
        """WindMouse algorithm must converge cleanly on target coordinates."""
        start = (50, 80)
        end = (450, 520)
        steps = generate_windmouse_path(start, end, gravity=9.0, wind=3.0)
        self.assertGreater(len(steps), 5)
        final_x, final_y, _ = steps[-1]
        self.assertEqual(final_x, end[0])
        self.assertEqual(final_y, end[1])

        # Verify all steps have positive delay
        for x, y, delay in steps:
            self.assertGreater(delay, 0.0)

    def test_fitts_profiler_duration(self):
        """Fitts's Law duration should scale monotonically with distance and speed preset."""
        d_short = 50.0
        d_long = 800.0
        t_fast_short = FittsProfiler.calculate_duration(d_short, speed="fast")
        t_norm_short = FittsProfiler.calculate_duration(d_short, speed="normal")
        t_slow_short = FittsProfiler.calculate_duration(d_short, speed="slow")

        self.assertLess(t_fast_short, t_norm_short)
        self.assertLess(t_norm_short, t_slow_short)

        t_norm_long = FittsProfiler.calculate_duration(d_long, speed="normal")
        self.assertGreater(t_norm_long, t_norm_short)

    def test_fitts_profiler_scheduling(self):
        """Scheduled path steps must have Minimum Jerk non-constant delay distributions."""
        points = [(i * 20, i * 20) for i in range(25)]
        target_dur = 0.45
        scheduled = FittsProfiler.schedule_path(points, total_duration=target_dur)
        self.assertEqual(len(scheduled), len(points))
        delays = [d for _, _, d in scheduled]
        # Verify delays are not completely uniform (anti-bot non-constant delay check)
        self.assertNotEqual(min(delays), max(delays))

    def test_overshoot_generation(self):
        """Overshoot generator produces valid points beyond target on high-probability runs."""
        start = (100, 100)
        end = (500, 500)
        dist = math.hypot(400, 400)
        # Forced probability 1.0
        ox = FittsProfiler.generate_overshoot(start, end, distance=dist, probability=1.0)
        self.assertIsNotNone(ox)
        # Distance from start to ox must be greater than distance from start to end
        dist_ox = math.hypot(ox[0] - start[0], ox[1] - start[1])
        self.assertGreater(dist_ox, dist)

    def test_stroke_generator(self):
        """Stroke generator must produce a continuous sequence respecting duration."""
        waypoints = [(100, 100), (200, 300), (400, 250), (600, 400)]
        target_duration = 0.8
        steps = generate_stroke_path(waypoints, duration=target_duration, smooth=True)
        self.assertGreater(len(steps), 20)
        self.assertEqual(steps[0][0], waypoints[0][0])
        self.assertEqual(steps[-1][0], waypoints[-1][0])


class TestHumanMotionPlatformIntegration(unittest.TestCase):
    """Integration tests for platform input engine and MCP tools."""

    def test_batch_actions_move_support(self):
        """execute_batch_actions must process 'move' and 'hover' actions with human_like=True."""
        batch = [
            {"action": "move", "x": 400, "y": 400, "human_like": True, "speed": "fast"},
            {"action": "sleep", "ms": 20},
            {"action": "move", "x": 450, "y": 450, "human_like": False},
        ]
        res = execute_batch_actions(batch)
        self.assertTrue(res["success"])
        self.assertEqual(res["executed_count"], 3)
        self.assertEqual(res["actions"][0]["action"], "move")
        self.assertTrue(res["actions"][0]["human_like"])
        self.assertEqual(res["actions"][2]["action"], "move")
        self.assertFalse(res["actions"][2]["human_like"])

    def test_batch_actions_stroke_support(self):
        """execute_batch_actions must process 'stroke' / 'brush' actions."""
        batch = [
            {
                "action": "stroke",
                "points": [[300, 300], [350, 350], [400, 300]],
                "button": "left",
                "duration": 0.05,
                "smooth": True,
            }
        ]
        res = execute_batch_actions(batch)
        self.assertTrue(res["success"])
        self.assertEqual(res["executed_count"], 1)
        self.assertEqual(res["actions"][0]["action"], "stroke")
        self.assertEqual(res["actions"][0]["point_count"], 3)

    def test_mcp_extra_mouse_move(self):
        """extra_mouse_move MCP tool must execute and report duration."""
        res = extra_mouse_move(x=350, y=350, human_like=True, speed="fast")
        self.assertTrue(res["success"])
        self.assertEqual(res["phys_x"], 350)
        self.assertEqual(res["phys_y"], 350)
        self.assertTrue(res["human_like"])
        self.assertGreater(res["duration_ms"], 0.0)

    @patch("extra.mcp.server.capture_screen", return_value=None)
    def test_mcp_extra_stroke(self, mock_cap):
        """extra_stroke MCP tool must execute multi-point continuous brush motion."""
        points = [[200, 200], [250, 280], [350, 250]]
        res = extra_stroke(points=points, button="left", duration=0.05, smooth=True)
        self.assertTrue(res["success"])
        self.assertEqual(res["point_count"], 3)
        self.assertEqual(res["button"], "left")
        self.assertGreater(res["duration_ms"], 0.0)


if __name__ == "__main__":
    unittest.main()
