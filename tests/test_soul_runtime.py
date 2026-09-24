"""
Unit & Integration Test Suite — Project SOUL (System One Ultra-fast Layer)
Validates execution provider detection, grammar constraints, decision logic, and sub-10ms latency.
Built using standard library unittest for zero external test runner dependency.
"""

import time
import unittest

from extra.core.soul import (
    DecisionType,
    SoulDecider,
    SoulDecision,
    get_soul_decider,
    get_soul_runtime,
)
from extra.core.soul.grammar import (
    format_boolean_prompt,
    format_choice_prompt,
    parse_boolean_response,
    parse_choice_response,
)
from extra.core.soul.runtime import SoulRuntimeManager
from extra.core.soul.schemas import SoulBoundingBox


class TestSoulRuntime(unittest.TestCase):
    """Tests hardware acceleration discovery and runtime lifecycle."""

    def test_singleton_runtime(self):
        rt1 = get_soul_runtime()
        rt2 = get_soul_runtime()
        self.assertIs(rt1, rt2)
        self.assertIsInstance(rt1, SoulRuntimeManager)

    def test_provider_discovery(self):
        rt = get_soul_runtime()
        providers = rt.get_execution_providers()
        self.assertIsInstance(providers, list)
        self.assertGreaterEqual(len(providers), 1)
        self.assertIn("CPUExecutionProvider", providers)

    def test_missing_model_graceful_fallback(self):
        rt = get_soul_runtime()
        session = rt.get_session("non_existent_model_xyz")
        self.assertIsNone(session)


class TestSoulGrammar(unittest.TestCase):
    """Tests constrained decoding, schema enforcement, and zero-hallucination parsing."""

    def test_format_prompts(self):
        bool_prompt = format_boolean_prompt("Is modal visible?", context="Title: Canva")
        self.assertIn("TRUE or FALSE", bool_prompt)
        self.assertIn("Title: Canva", bool_prompt)

        choice_prompt = format_choice_prompt("Current state", ["modal", "spinner", "normal"])
        self.assertIn("['modal', 'spinner', 'normal']", choice_prompt)

    def test_parse_boolean_exact(self):
        self.assertTrue(parse_boolean_response("true")[0])
        self.assertFalse(parse_boolean_response("FALSE")[0])
        self.assertTrue(parse_boolean_response("yes")[0])
        self.assertFalse(parse_boolean_response("no")[0])

    def test_parse_boolean_messy_strings(self):
        val, conf = parse_boolean_response("The answer is definitely True!")
        self.assertTrue(val)
        self.assertGreaterEqual(conf, 0.70)

        val, conf = parse_boolean_response("Result: False, no modal detected.")
        self.assertFalse(val)
        self.assertGreaterEqual(conf, 0.70)

    def test_parse_choice_strict(self):
        opts = ["modal_blocked", "spinner_active", "progressing", "idle"]

        # Exact match
        matched, conf = parse_choice_response("progressing", opts)
        self.assertEqual(matched, "progressing")
        self.assertGreaterEqual(conf, 0.90)

        # Substring / sentence
        matched, conf = parse_choice_response("The current screen is spinner_active right now.", opts)
        self.assertEqual(matched, "spinner_active")

        # Overlap fallback
        matched, _ = parse_choice_response("Looks like a modal block", opts)
        self.assertEqual(matched, "modal_blocked")


class TestSoulDecider(unittest.TestCase):
    """Tests the reflexive decision engine across real-world desktop automation scenarios."""

    def test_singleton_decider(self):
        d1 = get_soul_decider()
        d2 = get_soul_decider()
        self.assertIs(d1, d2)
        self.assertIsInstance(d1, SoulDecider)

    def test_decide_boolean_modal_positive(self):
        decider = get_soul_decider()
        context = {
            "window_title": "Canva — Open design link",
            "focused_control": "Please enter a valid design link",
        }
        res = decider.decide_boolean("Is the 'Open design link' popup active?", context=context)
        self.assertIsInstance(res, SoulDecision)
        self.assertEqual(res.decision_type, DecisionType.BOOLEAN)
        self.assertTrue(res.result)
        self.assertGreaterEqual(res.confidence, 0.85)
        self.assertTrue(res.is_confident)

    def test_decide_boolean_modal_negative(self):
        decider = get_soul_decider()
        context = {
            "window_title": "Calculator",
            "focused_control": "Display is 42",
        }
        res = decider.decide_boolean("Is an error dialog visible?", context=context)
        self.assertFalse(res.result)

    def test_decide_boolean_spinner(self):
        decider = get_soul_decider()
        context = "Status: Loading... Please wait for synchronization."
        res = decider.decide_boolean("Is the loading spinner active?", context=context)
        self.assertTrue(res.result)

    def test_decide_choice(self):
        decider = get_soul_decider()
        opts = ["error_dialog", "normal_workspace", "loading_spinner"]
        context = {"window_title": "Notepad — Untitled", "text": "All operations completed successfully."}
        res = decider.decide_choice("Classify active workspace state", opts, context=context)
        self.assertEqual(res.decision_type, DecisionType.CHOICE)
        self.assertEqual(res.result, "normal_workspace")

    def test_evaluate_condition_helper(self):
        decider = get_soul_decider()
        ctx = {"window_title": "Paint", "focused_control": "Canvas"}
        self.assertTrue(decider.evaluate_condition("Is 'Canvas' visible?", ctx))
        self.assertFalse(decider.evaluate_condition("Is 'Error' visible?", ctx))

    def test_latency_sub_10ms_benchmark(self):
        """Strict acceptance test: Assert median decision latency is under 10ms."""
        decider = get_soul_decider()
        latencies = []
        ctx = {"window_title": "Microsoft Edge", "url": "https://example.com"}

        for _ in range(50):
            t0 = time.perf_counter()
            decider.decide_boolean("Is browser active?", context=ctx)
            latencies.append((time.perf_counter() - t0) * 1000.0)

        latencies.sort()
        median_latency = latencies[len(latencies) // 2]
        print(f"\n[BENCHMARK] SOUL Decider 50-run Median Latency: {median_latency:.3f} ms")
        self.assertLess(median_latency, 10.0, f"SOUL latency exceeded 10ms: {median_latency:.2f}ms")


class TestSoulBoundingBox(unittest.TestCase):
    """Tests spatial geometry dataclass for Tier 2 grounding."""

    def test_box_properties(self):
        box = SoulBoundingBox(ymin=100.0, xmin=200.0, ymax=300.0, xmax=600.0, label="button")
        self.assertEqual(box.center, (400.0, 200.0))
        self.assertEqual(box.width, 400.0)
        self.assertEqual(box.height, 200.0)


if __name__ == "__main__":
    unittest.main()
