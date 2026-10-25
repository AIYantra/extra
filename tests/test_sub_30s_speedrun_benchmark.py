"""
End-to-End Speedrun Benchmark Suite for Project Extra.
Verifies the complete 5-stage desktop automation workflow under 'turbo' execution mode:
1. Start Clock Timer
2. Fetch live NASDAQ gainers and launch in Notepad
3. Snap open windows side-by-side
4. Extract clipboard contents
5. Stop/Pause Clock Timer

Target: Complete multi-application pipeline executed on live desktop in < 15.0 seconds (well under the 30.0s requirement).
"""

from __future__ import annotations

import json
import os
import sys
import time
import unittest
from pathlib import Path

from extra.core.mode import ExecutionMode, set_execution_mode
from extra.mcp.server import (
    extra_set_mode,
    extra_subtask_run,
    extra_snap_layout,
    extra_task_start,
)


class TestSub30sSpeedrunBenchmark(unittest.TestCase):
    """Live Speedrun Benchmark Suite."""

    @classmethod
    def setUpClass(cls):
        set_execution_mode(ExecutionMode.TURBO)

    def test_01_macro_intent_compilation_speed(self):
        """Pure intent compilation on-device must take < 5ms per intent."""
        from extra.core.subtask import SubtaskRunner
        runner = SubtaskRunner()

        intents = [
            "start clock timer",
            "calculate 145 * 28 in calc",
            "snap Clock and Calculator side by side",
            "copy all text",
            "stop timer",
        ]
        t0 = time.perf_counter()
        compiled = [runner.compile_intent(i) for i in intents]
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        for idx, acts in enumerate(compiled):
            self.assertTrue(len(acts) > 0, f"Intent '{intents[idx]}' failed to compile")

        avg_ms = elapsed_ms / len(intents)
        print(f"\n[BENCHMARK] Intent Compilation: {len(intents)} intents compiled in {elapsed_ms:.2f}ms (avg: {avg_ms:.3f}ms/intent)")
        self.assertLess(avg_ms, 5.0, "Intent compilation exceeded 5ms budget")

    @unittest.skipIf(os.environ.get("CI") == "true" or sys.platform != "win32", "Live GUI speedrun skipped in headless CI")
    def test_02_end_to_end_turbo_pipeline_live(self):
        """Executes the complete 5-stage automation pipeline live in < 15.0 seconds."""
        timings = {}
        t_global_start = time.perf_counter()

        # Phase 0: Task Initialization in Turbo Mode
        t0 = time.perf_counter()
        init_res = extra_task_start(task_name="Sub-30s Speedrun Benchmark", mode="turbo")
        timings["task_start"] = (time.perf_counter() - t0) * 1000.0
        self.assertTrue(init_res["success"])
        self.assertEqual(init_res["mode"], "turbo")

        # Step 1: Launch Clock and Start Timer
        t0 = time.perf_counter()
        step1 = extra_subtask_run(intent="start clock timer", mode="turbo")
        timings["step1_clock_timer"] = (time.perf_counter() - t0) * 1000.0
        self.assertTrue(step1["success"], f"Step 1 failed: {step1.get('error')}")

        # Step 2: Fetch NASDAQ Gainers and Open in Notepad
        t0 = time.perf_counter()
        step2 = extra_subtask_run(intent="fetch nasdaq gainers and open in notepad", mode="turbo")
        timings["step2_nasdaq_notepad"] = (time.perf_counter() - t0) * 1000.0
        self.assertTrue(step2["success"], f"Step 2 failed: {step2.get('error')}")

        # Verify artifact on disk
        nasdaq_file = Path.home() / ".extra" / "workspace" / "nasdaq_top5.txt"
        self.assertTrue(nasdaq_file.exists(), "nasdaq_top5.txt was not created")
        report_text = nasdaq_file.read_text(encoding="utf-8")
        self.assertIn("Top 5 NASDAQ Gainers", report_text)

        # Step 3: Snap Clock and Notepad (or open Calculator if Notepad not active)
        t0 = time.perf_counter()
        # Ensure Calculator or Notepad is present
        from extra.mcp.server import extra_launch
        extra_launch(app_name="calc")
        step3 = extra_snap_layout(layout="side_by_side", left_window="Clock", right_window="Calculator")
        timings["step3_snap_layout"] = (time.perf_counter() - t0) * 1000.0
        self.assertTrue(step3.get("success", False), f"Step 3 failed: {step3.get('error')}")

        # Step 4: Extract Data via Clipboard
        t0 = time.perf_counter()
        step4 = extra_subtask_run(intent="copy all text", mode="turbo")
        timings["step4_copy_data"] = (time.perf_counter() - t0) * 1000.0
        self.assertTrue(step4["success"], f"Step 4 failed: {step4.get('error')}")

        # Step 5: Stop / Pause Clock Timer
        t0 = time.perf_counter()
        step5 = extra_subtask_run(intent="stop timer", mode="turbo")
        timings["step5_stop_timer"] = (time.perf_counter() - t0) * 1000.0
        self.assertTrue(step5["success"], f"Step 5 failed: {step5.get('error')}")

        total_wall_clock_sec = time.perf_counter() - t_global_start

        # Print Benchmark Telemetry Table
        print("\n" + "=" * 65)
        print("  SUB-30S AUTOMATION SPEEDRUN BENCHMARK RESULTS (TURBO MODE)")
        print("=" * 65)
        for stage, ms in timings.items():
            print(f"  • {stage:<25} : {ms:8.2f} ms")
        print("-" * 65)
        print(f"  TOTAL WORKFLOW DURATION    : {total_wall_clock_sec:8.2f} s")
        print(f"  BASELINE AGY HIGH LATENCY  :   479.00 s (79 turns)")
        print(f"  BASELINE AGY LOW LATENCY   :   476.00 s (53 turns)")
        print(f"  SPEEDUP vs BASELINE        :    {476.0 / total_wall_clock_sec:6.1f}x faster!")
        print("=" * 65)

        # Benchmark assertions: Must complete in < 15 seconds (target is < 30s)
        self.assertLess(total_wall_clock_sec, 15.0, f"Speedrun took {total_wall_clock_sec:.2f}s, exceeding 15s budget")


if __name__ == "__main__":
    unittest.main()
