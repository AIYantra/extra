"""
Unit and Integration Tests for Project Extra Execution Modes and Compact UI Serialization.
Verifies runtime mode switching (turbo, balanced, smart), sleep scaling, and compact UI serialization.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from extra.core.mode import (
    ExecutionMode,
    ModeConfig,
    MODE_PROFILES,
    get_execution_mode,
    get_mode_config,
    set_execution_mode,
)
from extra.mcp.server import extra_set_mode, extra_inspect_ui, extra_batch_actions, extra_task_start


class TestExecutionModes(unittest.TestCase):
    """Test suite for Extra's runtime speed and verification mode engine."""

    def setUp(self):
        self.original_env = os.environ.get("EXTRA_SPEED_MODE")
        set_execution_mode(ExecutionMode.BALANCED)

    def tearDown(self):
        if self.original_env is not None:
            set_execution_mode(self.original_env)
        else:
            set_execution_mode(ExecutionMode.BALANCED)

    def test_mode_alias_parsing(self):
        """Mode parsing must gracefully handle colloquial aliases from LLMs and users."""
        # Turbo / Low / Fast
        self.assertEqual(ExecutionMode.from_string("turbo"), ExecutionMode.TURBO)
        self.assertEqual(ExecutionMode.from_string("low"), ExecutionMode.TURBO)
        self.assertEqual(ExecutionMode.from_string("fast"), ExecutionMode.TURBO)
        self.assertEqual(ExecutionMode.from_string("lightning"), ExecutionMode.TURBO)
        self.assertEqual(ExecutionMode.from_string("speed"), ExecutionMode.TURBO)

        # Balanced / Medium / Default
        self.assertEqual(ExecutionMode.from_string("balanced"), ExecutionMode.BALANCED)
        self.assertEqual(ExecutionMode.from_string("medium"), ExecutionMode.BALANCED)
        self.assertEqual(ExecutionMode.from_string("default"), ExecutionMode.BALANCED)
        self.assertEqual(ExecutionMode.from_string("unknown_random_string"), ExecutionMode.BALANCED)

        # Smart / High / Deep
        self.assertEqual(ExecutionMode.from_string("smart"), ExecutionMode.SMART)
        self.assertEqual(ExecutionMode.from_string("high"), ExecutionMode.SMART)
        self.assertEqual(ExecutionMode.from_string("deep"), ExecutionMode.SMART)
        self.assertEqual(ExecutionMode.from_string("full"), ExecutionMode.SMART)
        self.assertEqual(ExecutionMode.from_string("safe"), ExecutionMode.SMART)

    def test_mode_config_profiles(self):
        """Each execution profile must have appropriate pacing and verification guardrails."""
        turbo = get_mode_config(ExecutionMode.TURBO)
        self.assertFalse(turbo.auto_settle)
        self.assertEqual(turbo.max_inspect_elements, 10)
        self.assertTrue(turbo.compact_ui)
        self.assertTrue(turbo.strip_heavy_attributes)
        self.assertLessEqual(turbo.sleep_scale, 0.1)
        self.assertLessEqual(turbo.max_sleep_ms, 50.0)

        balanced = get_mode_config(ExecutionMode.BALANCED)
        self.assertTrue(balanced.auto_settle)
        self.assertEqual(balanced.max_inspect_elements, 15)
        self.assertTrue(balanced.compact_ui)
        self.assertTrue(balanced.strip_heavy_attributes)

        smart = get_mode_config(ExecutionMode.SMART)
        self.assertTrue(smart.auto_settle)
        self.assertEqual(smart.max_inspect_elements, 30)
        self.assertFalse(smart.compact_ui)
        self.assertFalse(smart.strip_heavy_attributes)
        self.assertEqual(smart.sleep_scale, 1.0)
        self.assertTrue(smart.proactive_memory_recall)

    def test_runtime_mode_switching(self):
        """set_execution_mode must update global active mode and environment variable."""
        set_execution_mode("turbo")
        self.assertEqual(get_execution_mode(), ExecutionMode.TURBO)
        self.assertEqual(os.environ.get("EXTRA_SPEED_MODE"), "turbo")

        set_execution_mode("smart")
        self.assertEqual(get_execution_mode(), ExecutionMode.SMART)
        self.assertEqual(os.environ.get("EXTRA_SPEED_MODE"), "smart")

    def test_extra_set_mode_tool(self):
        """MCP tool extra_set_mode must return success and structured configuration."""
        res = extra_set_mode("turbo")
        self.assertTrue(res["success"])
        self.assertEqual(res["mode"], "turbo")
        self.assertIn("config", res)
        self.assertFalse(res["config"]["auto_settle"])

    def test_extra_task_start_mode_override(self):
        """extra_task_start must allow setting execution mode on session initiation."""
        res = extra_task_start(task_name="Speed Test Task", mode="turbo")
        self.assertTrue(res["success"])
        self.assertEqual(res["mode"], "turbo")
        self.assertEqual(get_execution_mode(), ExecutionMode.TURBO)

    @patch("extra.mcp.server._uia_plane")
    def test_compact_ui_serialization_prunes_bloat(self, mock_uia):
        """extra_inspect_ui in balanced/turbo mode must return compact representation under 1KB."""
        # Create a mock element with heavy COM attributes
        mock_el = MagicMock()
        mock_el.to_dict.return_value = {
            "element_id": 1,
            "name": "PlayPauseButton",
            "control_type": "Button",
            "center": [250, 350],
            "bounding_box": [240, 340, 260, 360],
            "class_name": "Windows.UI.Core.DirectUI",
            "runtime_id": [42, 100, 200, 300, 400],
            "help_text": "Pauses the running timer immediately",
            "is_keyboard_focusable": True,
            "is_enabled": True,
        }
        mock_uia.inspect_window.return_value = [mock_el]

        # Call extra_inspect_ui in balanced mode
        res = extra_inspect_ui(window_title="Clock", mode="balanced")
        self.assertTrue(res["success"])
        self.assertEqual(res["count"], 1)
        self.assertIn("ui_summary", res)
        self.assertIn("ID 1 | Button 'PlayPauseButton'", res["ui_summary"])

        # Heavy attributes must be stripped from returned elements list
        elem = res["elements"][0]
        self.assertIn("element_id", elem)
        self.assertIn("center", elem)
        self.assertIn("bounding_box", elem)
        self.assertNotIn("runtime_id", elem)
        self.assertNotIn("class_name", elem)
        self.assertNotIn("help_text", elem)

        # Output payload size check
        payload_bytes = len(json.dumps(res))
        self.assertLess(payload_bytes, 1000, f"Payload exceeded 1KB: {payload_bytes} bytes")

    @patch("extra.mcp.server.execute_batch_actions")
    def test_batch_actions_sleep_scaling_in_turbo(self, mock_exec):
        """extra_batch_actions in turbo mode must scale down 2000ms sleeps to <= 50ms."""
        mock_exec.return_value = {"success": True, "executed_count": 1}
        actions = [{"action": "sleep", "ms": 2000}]
        res = extra_batch_actions(actions=actions, mode="turbo")
        self.assertTrue(res["success"])
        self.assertEqual(res["mode"], "turbo")
        called_actions = mock_exec.call_args[0][0]
        self.assertEqual(called_actions[0]["ms"], 50.0)



    def test_cli_mode_and_modeset_commands(self):
        """Tests that CLI 'extra mode' and 'extra modeset' switch and display modes cleanly."""
        import argparse
        import io
        from contextlib import redirect_stdout
        from extra.cli import cmd_mode

        # Set to turbo via CLI
        args = argparse.Namespace(mode="turbo")
        ret = cmd_mode(args)
        self.assertEqual(ret, 0)
        self.assertEqual(get_execution_mode(), ExecutionMode.TURBO)

        # View current mode via CLI (no arg)
        f = io.StringIO()
        with redirect_stdout(f):
            ret_view = cmd_mode(argparse.Namespace(mode=None))
        self.assertEqual(ret_view, 0)
        self.assertIn("TURBO", f.getvalue())

        # Set to smart via CLI modeset alias
        ret_smart = cmd_mode(argparse.Namespace(mode="smart"))
        self.assertEqual(ret_smart, 0)
        self.assertEqual(get_execution_mode(), ExecutionMode.SMART)

        # Restore balanced
        cmd_mode(argparse.Namespace(mode="balanced"))
        self.assertEqual(get_execution_mode(), ExecutionMode.BALANCED)

    def test_mode_loads_from_config_file(self):
        """Verifies _load_initial_mode reads speed_mode from config.json when env var is absent."""
        import tempfile
        from extra.core.mode import _load_initial_mode
        with tempfile.TemporaryDirectory() as tmp_dir:
            extra_dir = Path(tmp_dir) / ".extra"
            extra_dir.mkdir(parents=True, exist_ok=True)
            (extra_dir / "config.json").write_text(json.dumps({"speed_mode": "turbo"}), encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True), patch("pathlib.Path.home", return_value=Path(tmp_dir)):
                loaded = _load_initial_mode()
                self.assertEqual(loaded, ExecutionMode.TURBO)


if __name__ == "__main__":
    unittest.main()
