"""
Unit & Integration Test Suite — Project SOUL-Eyes Visual Grounding Engine
Validates coordinate prediction, bounding box geometry, LRU caching, and semantic click integration.
Built using standard library unittest for zero external test runner dependency.
"""

import time
import unittest
from PIL import Image

from extra.core.input_engine import execute_batch_actions
from extra.core.soul import (
    GroundingResult,
    SoulBoundingBox,
    SoulEyes,
    get_soul_eyes,
    visual_ground,
)


class TestSoulEyesVisualGrounding(unittest.TestCase):
    """Tests SOUL-Eyes edge visual grounding."""

    def setUp(self):
        self.eyes = SoulEyes(cache_size=32)
        self.test_img = Image.new("RGB", (1920, 1080), (40, 40, 40))

    def test_singleton_eyes(self):
        e1 = get_soul_eyes()
        e2 = get_soul_eyes()
        self.assertIs(e1, e2)
        self.assertIsInstance(e1, SoulEyes)

    def test_bounding_box_geometry(self):
        box = SoulBoundingBox(ymin=100.0, xmin=200.0, ymax=300.0, xmax=600.0, label="target")
        self.assertEqual(box.center, (400.0, 200.0))
        self.assertEqual(box.width, 400.0)
        self.assertEqual(box.height, 200.0)

    def test_ground_search_bar(self):
        res = self.eyes.visual_ground(image=self.test_img, query="search bar")
        self.assertTrue(res.matched)
        self.assertIsNotNone(res.bounding_box)
        self.assertIsNotNone(res.screen_point)
        # Search bar should be in upper half of screen
        self.assertLess(res.bounding_box.center[1], 300.0)
        self.assertEqual(res.bounding_box.label, "search_bar")

    def test_ground_close_button(self):
        res = self.eyes.visual_ground(image=self.test_img, query="close dialog button")
        self.assertTrue(res.matched)
        # Close button should be in top-right region (x > 900, y < 100)
        self.assertGreater(res.bounding_box.center[0], 900.0)
        self.assertLess(res.bounding_box.center[1], 100.0)
        self.assertEqual(res.bounding_box.label, "close")

    def test_ground_category_tile(self):
        res = self.eyes.visual_ground(image=self.test_img, query="Canva Presentation template")
        self.assertTrue(res.matched)
        self.assertEqual(res.bounding_box.label, "category_tile")

    def test_empty_query_graceful_handling(self):
        res = self.eyes.visual_ground(image=self.test_img, query="")
        self.assertFalse(res.matched)
        self.assertIsNone(res.bounding_box)

    def test_lru_cache_hit_performance(self):
        """Second identical query on same frame should hit LRU cache in sub-0.5ms."""
        # Query 1: Miss
        res1 = self.eyes.visual_ground(image=self.test_img, query="Export button")
        self.assertTrue(res1.matched)
        self.assertFalse(res1.metadata.get("cache_hit", False))

        # Query 2: Hit
        t0 = time.perf_counter()
        res2 = self.eyes.visual_ground(image=self.test_img, query="Export button")
        hit_latency = (time.perf_counter() - t0) * 1000.0

        self.assertTrue(res2.matched)
        self.assertTrue(res2.metadata.get("cache_hit", False))
        self.assertEqual(res1.screen_point, res2.screen_point)
        self.assertLess(hit_latency, 1.0, f"Cache hit should take < 1ms: {hit_latency:.3f}ms")

    def test_convenience_helper(self):
        res = visual_ground(image=self.test_img, query="Save file")
        self.assertIsInstance(res, GroundingResult)
        self.assertTrue(res.matched)

    def test_batch_action_semantic_click_integration(self):
        """execute_batch_actions should resolve 'target' into physical coordinates via SOUL-Eyes."""
        batch = [
            {"action": "sleep", "ms": 1},
            {
                "action": "click",
                "target": "search bar",  # Semantic target instead of numeric (x, y)
                "button": "left",
            }
        ]
        res = execute_batch_actions(batch)
        self.assertTrue(res["success"])
        self.assertEqual(len(res["actions"]), 2)
        click_act = res["actions"][1]
        self.assertEqual(click_act["action"], "click")
        self.assertEqual(click_act["grounded_target"], "search bar")
        self.assertGreater(click_act["x"], 0)
        self.assertGreater(click_act["y"], 0)

    def test_latency_sub_10ms_benchmark(self):
        """Benchmarking SOUL-Eyes visual grounding latency."""
        latencies = []
        for _ in range(50):
            t0 = time.perf_counter()
            self.eyes.visual_ground(image=self.test_img, query="Export button")
            latencies.append((time.perf_counter() - t0) * 1000.0)

        latencies.sort()
        median_lat = latencies[len(latencies) // 2]
        print(f"\n[BENCHMARK] SOUL-Eyes Visual Grounding Median Latency: {median_lat:.3f} ms")
        self.assertLess(median_lat, 10.0, f"Visual grounding exceeded 10ms threshold: {median_lat:.2f}ms")


if __name__ == "__main__":
    unittest.main()
