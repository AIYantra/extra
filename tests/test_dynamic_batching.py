"""
Unit & Integration Test Suite — Project SOUL Dynamic Batch Actions
Validates in-engine reflexive branching ('eval', 'assert', 'wait_for_state') in execute_batch_actions.
Built using standard library unittest for zero external test runner dependency.
"""

import time
import unittest
from unittest.mock import patch

from extra.core.input_engine import execute_batch_actions


class TestDynamicBatchActions(unittest.TestCase):
    """Tests SOUL-driven dynamic execution in execute_batch_actions."""

    def test_eval_branch_true(self):
        """When condition evaluates to True, if_true actions should execute."""
        batch = [
            {"action": "sleep", "ms": 1},
            {
                "action": "eval",
                "condition": "Is modal dialog visible?",
                "context": {"window_title": "Canva — Open design link dialog"},
                "if_true": [
                    {"action": "sleep", "ms": 2},
                    {"action": "sleep", "ms": 3},
                ],
                "if_false": [
                    {"action": "sleep", "ms": 500},  # Must NOT execute
                ],
            },
        ]
        res = execute_batch_actions(batch)
        self.assertTrue(res["success"])
        actions = res["actions"]

        # Expected: sleep (1ms), eval, sub-sleep (2ms), sub-sleep (3ms)
        self.assertEqual(len(actions), 4)
        eval_action = actions[1]
        self.assertEqual(eval_action["action"], "eval")
        self.assertTrue(eval_action["result"])
        self.assertEqual(eval_action["branch"], "if_true")
        self.assertEqual(eval_action["sub_actions_count"], 2)

        # Check sub-actions
        self.assertEqual(actions[2]["action"], "sleep")
        self.assertEqual(actions[2]["ms"], 2)
        self.assertEqual(actions[3]["action"], "sleep")
        self.assertEqual(actions[3]["ms"], 3)

    def test_eval_branch_false(self):
        """When condition evaluates to False, if_false actions should execute."""
        batch = [
            {
                "action": "eval",
                "condition": "Is an error dialog visible?",
                "context": {"window_title": "Calculator", "focused_control": "Display 42"},
                "if_true": [
                    {"action": "sleep", "ms": 500},  # Must NOT execute
                ],
                "if_false": [
                    {"action": "sleep", "ms": 5},
                ],
            }
        ]
        res = execute_batch_actions(batch)
        self.assertTrue(res["success"])
        actions = res["actions"]

        self.assertEqual(len(actions), 2)
        eval_action = actions[0]
        self.assertEqual(eval_action["action"], "eval")
        self.assertFalse(eval_action["result"])
        self.assertEqual(eval_action["branch"], "if_false")
        self.assertEqual(actions[1]["action"], "sleep")
        self.assertEqual(actions[1]["ms"], 5)

    def test_eval_nested_branching(self):
        """Tests multi-level nested eval branching up to max depth."""
        batch = [
            {
                "action": "eval",
                "condition": "Is 'Canva' active?",
                "context": {"window_title": "Canva"},
                "if_true": [
                    {
                        "action": "eval",
                        "condition": "Is 'Open' dialog present?",
                        "context": {"window_title": "Canva — Open file"},
                        "if_true": [
                            {"action": "sleep", "ms": 10},
                        ],
                    }
                ],
            }
        ]
        res = execute_batch_actions(batch)
        self.assertTrue(res["success"])
        self.assertEqual(len(res["actions"]), 3)
        self.assertEqual(res["actions"][0]["action"], "eval")
        self.assertEqual(res["actions"][1]["action"], "eval")
        self.assertEqual(res["actions"][2]["action"], "sleep")

    def test_assert_passing(self):
        """When assertion passes, subsequent actions execute uninterrupted."""
        batch = [
            {"action": "sleep", "ms": 1},
            {
                "action": "assert",
                "condition": "Is 'Presentation' visible?",
                "context": {"window_title": "Canva — Presentation Post"},
                "on_fail": "abort",
            },
            {"action": "sleep", "ms": 2},
        ]
        res = execute_batch_actions(batch)
        self.assertTrue(res["success"])
        self.assertEqual(len(res["actions"]), 3)
        self.assertTrue(res["actions"][1]["passed"])

    def test_assert_failing_abort(self):
        """When assertion fails with on_fail='abort', batch halts immediately."""
        batch = [
            {"action": "sleep", "ms": 1},
            {
                "action": "assert",
                "condition": "Is error dialog present?",
                "context": {"window_title": "Calculator"},  # No error
                "on_fail": "abort",
            },
            {"action": "sleep", "ms": 999},  # Must NOT execute
        ]
        res = execute_batch_actions(batch)
        self.assertFalse(res["success"])
        self.assertIn("error", res)
        self.assertIn("Assertion failed on condition", res["error"])
        # Should only execute sleep and the failed assert
        self.assertEqual(len(res["actions"]), 2)
        self.assertFalse(res["actions"][1]["passed"])

    def test_assert_failing_continue(self):
        """When assertion fails with on_fail='continue', execution proceeds."""
        batch = [
            {
                "action": "assert",
                "condition": "Is error dialog present?",
                "context": {"window_title": "Calculator"},
                "on_fail": "continue",
            },
            {"action": "sleep", "ms": 1},
        ]
        res = execute_batch_actions(batch)
        self.assertTrue(res["success"])
        self.assertEqual(len(res["actions"]), 2)
        self.assertFalse(res["actions"][0]["passed"])
        self.assertEqual(res["actions"][1]["action"], "sleep")

    def test_wait_for_state_immediate(self):
        """When target state is already met, wait_for_state returns immediately."""
        batch = [
            {
                "action": "wait_for_state",
                "condition": "Is 'Notepad' active?",
                "context": {"window_title": "Notepad — Notes.txt"},
                "timeout_ms": 1000,
                "poll_interval_ms": 20,
            }
        ]
        t0 = time.perf_counter()
        res = execute_batch_actions(batch)
        dur_ms = (time.perf_counter() - t0) * 1000.0

        self.assertTrue(res["success"])
        self.assertEqual(len(res["actions"]), 1)
        self.assertTrue(res["actions"][0]["satisfied"])
        self.assertLess(dur_ms, 200.0, "Immediate state should return in < 200ms")

    def test_eval_benchmark_sub_millisecond(self):
        """Benchmarking SOUL eval inside a batch action."""
        batch = [
            {
                "action": "eval",
                "condition": "Is dialog open?",
                "context": {"window_title": "Open File Dialog"},
                "if_true": [{"action": "sleep", "ms": 0}],
            }
        ]
        latencies = []
        for _ in range(50):
            t0 = time.perf_counter()
            execute_batch_actions(batch)
            latencies.append((time.perf_counter() - t0) * 1000.0)

        latencies.sort()
        median_lat = latencies[len(latencies) // 2]
        print(f"\n[BENCHMARK] SOUL Dynamic Batch Action Median Latency: {median_lat:.3f} ms")
        self.assertLess(median_lat, 5.0, "Dynamic batch action evaluation should be < 5ms")


if __name__ == "__main__":
    unittest.main()
