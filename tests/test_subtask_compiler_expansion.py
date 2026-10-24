"""
Unit and Integration Tests for Project Extra Deep Macro Intent Compilation and Mode Integration.
Validates:
1. Clock / Timer / Stopwatch macro intent compilation.
2. Atomic note creation & direct Notepad file launch fast-path.
3. Market / NASDAQ Gainers automatic retrieval and notepad presentation.
4. Compound intent pipeline decomposition (chaining via 'and', ';', 'then').
5. Execution mode integration (turbo sleep scaling, settle elimination) in SubtaskRunner.
6. MCP tool extra_subtask_run mode dispatch.
"""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from extra.core.mode import ExecutionMode, set_execution_mode
from extra.core.subtask import SubtaskRunner, run_subtask
from extra.mcp.server import extra_subtask_run


class TestSubtaskCompilerExpansion(unittest.TestCase):
    """Test suite for expanded macro intent compilation and mode execution."""

    def setUp(self):
        self.runner = SubtaskRunner()
        set_execution_mode(ExecutionMode.BALANCED)

    def tearDown(self):
        set_execution_mode(ExecutionMode.BALANCED)

    def test_clock_timer_and_stopwatch_macros(self):
        """Clock timer and stopwatch intents must compile to deterministic UI actions."""
        # 1. Start timer
        start_timer = self.runner.compile_intent("start clock timer")
        self.assertTrue(len(start_timer) >= 5)
        self.assertEqual(start_timer[0]["action"], "launch")
        self.assertEqual(start_timer[0]["app_name"], "clock")
        self.assertEqual(start_timer[1]["action"], "focus")
        self.assertEqual(start_timer[3]["action"], "hotkey")
        self.assertEqual(start_timer[3]["keys"], ["ctrl", "1"])  # Timer tab
        self.assertEqual(start_timer[5]["action"], "hotkey")
        self.assertEqual(start_timer[5]["keys"], ["space"])

        # 2. Start stopwatch
        start_sw = self.runner.compile_intent("start stopwatch")
        self.assertTrue(len(start_sw) >= 5)
        self.assertEqual(start_sw[3]["keys"], ["ctrl", "3"])  # Stopwatch tab
        self.assertEqual(start_sw[5]["keys"], ["space"])

        # 3. Pause / Stop timer
        pause_timer = self.runner.compile_intent("stop timer")
        self.assertEqual(pause_timer[0]["action"], "focus")
        self.assertEqual(pause_timer[0]["window_title"], "Clock")
        self.assertEqual(pause_timer[2]["action"], "hotkey")
        self.assertEqual(pause_timer[2]["keys"], ["space"])

        # 4. Reset stopwatch
        reset_sw = self.runner.compile_intent("reset stopwatch")
        self.assertEqual(reset_sw[0]["action"], "focus")
        self.assertEqual(reset_sw[2]["action"], "hotkey")
        self.assertEqual(reset_sw[2]["keys"], ["r"])

    def test_notepad_atomic_file_fastpath(self):
        """Writing content to notepad must pre-write to workspace and launch with path."""
        intent = "save 'Q3 Financial Briefing: Revenue up 24%' to notepad as q3_brief.txt"
        actions = self.runner.compile_intent(intent)
        self.assertTrue(len(actions) >= 2)
        self.assertEqual(actions[0]["action"], "launch")
        self.assertEqual(actions[0]["app_name"], "notepad")
        self.assertTrue(len(actions[0]["args"]) == 1)

        written_path = Path(actions[0]["args"][0])
        self.assertTrue(written_path.exists())
        self.assertIn("q3_brief.txt", str(written_path))
        file_content = written_path.read_text(encoding="utf-8")
        self.assertIn("Q3 Financial Briefing: Revenue up 24%", file_content)

    def test_nasdaq_gainers_fastpath(self):
        """Fetching NASDAQ gainers must compile formatted report and launch in Notepad."""
        intent = "fetch nasdaq gainers and open in notepad"
        actions = self.runner.compile_intent(intent)
        self.assertTrue(len(actions) >= 2)
        self.assertEqual(actions[0]["action"], "launch")
        self.assertEqual(actions[0]["app_name"], "notepad")

        gainers_path = Path(actions[0]["args"][0])
        self.assertTrue(gainers_path.exists())
        text = gainers_path.read_text(encoding="utf-8")
        self.assertIn("Top 5 NASDAQ Gainers", text)
        self.assertIn("1.", text)
        self.assertIn("2.", text)
        self.assertIn("%", text)

    def test_compound_intent_pipeline_chaining(self):
        """Compound intents joined by 'and', ';', or 'then' must chain into one pipeline."""
        # 1. Chained with ';'
        chained_semi = self.runner.compile_intent("calculate 145*28 ; copy all")
        self.assertTrue(len(chained_semi) > 8)
        self.assertEqual(chained_semi[0]["action"], "launch")
        self.assertEqual(chained_semi[0]["app_name"], "calc")
        self.assertEqual(chained_semi[-1]["action"], "read_clipboard")

        # 2. Chained with 'and'
        chained_and = self.runner.compile_intent("start clock timer and open notepad")
        self.assertTrue(len(chained_and) >= 8)
        self.assertEqual(chained_and[0]["app_name"], "clock")
        has_notepad = any(a.get("app_name") == "notepad" for a in chained_and)
        self.assertTrue(has_notepad)

    @patch("extra.core.subtask.execute_batch_actions")
    def test_mode_scaling_in_subtask_runner(self, mock_exec):
        """SubtaskRunner in turbo mode must scale sleeps down to <= 50ms and bypass auto_settle."""
        mock_exec.return_value = {"success": True, "executed": [{"action": "sleep", "ms": 50.0}]}
        actions = [{"action": "sleep", "ms": 2000}]

        res = run_subtask(actions=actions, mode="turbo")
        self.assertTrue(res.success)
        self.assertEqual(res.mode, "turbo")

        call_args = mock_exec.call_args
        dispatched_actions = call_args[0][0]
        # 2000ms sleep scaled down to 50ms
        self.assertEqual(dispatched_actions[0]["ms"], 50.0)
        # auto_settle disabled in turbo
        self.assertFalse(call_args[1]["auto_settle"])

    @patch("extra.core.subtask.execute_batch_actions")
    def test_mcp_extra_subtask_run_mode(self, mock_exec):
        """MCP tool extra_subtask_run must accept mode parameter and return mode in response."""
        mock_exec.return_value = {"success": True, "executed": [{"action": "hotkey", "keys": ["ctrl", "c"]}]}
        res = extra_subtask_run(intent="copy all text", mode="turbo")
        self.assertTrue(res["success"])
        self.assertEqual(res["mode"], "turbo")


if __name__ == "__main__":
    unittest.main()
