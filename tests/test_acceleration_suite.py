"""
Tests for Extra Ultra-Fast Computer Use Acceleration Engine.

Validates:
1. execute_batch_actions (atomic hardware input batching for clicks, typing, hotkeys, delays).
2. Win32 programmatic window snapping (get_work_area, snap_window, snap_layout).
3. execute_fs_batch (atomic directory tree creation, file organization, renaming, and deletion).
4. MCP tool schema registration and execution for extra_batch_actions, extra_snap_layout, extra_fs_batch.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from extra.core.focus import get_work_area, snap_layout, snap_window
from extra.core.input_engine import execute_batch_actions
from extra.fastpath.fs import execute_fs_batch
from extra.mcp.server import (
    extra_batch_actions,
    extra_fs_batch,
    extra_snap_layout,
    server,
)


PLATFORM_NAME = "windows" if sys.platform == "win32" else ("linux" if sys.platform.startswith("linux") else "macos")


class TestAccelerationSuite(unittest.TestCase):
    """Test suite for high-speed batching, zero-turn snapping, and fast-path fs tools."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="extra_test_fs_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ── 1. Batch Actions Tests ─────────────────────────────────────────────────

    @patch(f"extra.core.platform.{PLATFORM_NAME}.input_engine.send_hotkey")
    @patch(f"extra.core.platform.{PLATFORM_NAME}.input_engine.instant_type")
    @patch(f"extra.core.platform.{PLATFORM_NAME}.input_engine.mouse_click")
    def test_execute_batch_actions_sequence(self, mock_click, mock_type, mock_hotkey):
        """Verify compound action sequences execute atomically in a single dispatch."""
        actions = [
            {"action": "hotkey", "keys": ["ctrl", "t"], "settle_ms": 10},
            {"action": "type", "text": "about:blank", "press_enter": True, "settle_ms": 10},
            {"action": "click", "x": 100, "y": 200, "button": "left", "clicks": 1, "settle_ms": 10},
            {"action": "sleep", "ms": 50},
        ]
        res = execute_batch_actions(actions)

        self.assertTrue(res["success"])
        self.assertEqual(res["executed_count"], 4)
        self.assertGreater(res["total_duration_ms"], 0)

        mock_hotkey.assert_called_once_with(["ctrl", "t"])
        mock_type.assert_called_once_with("about:blank", press_enter=True)
        mock_click.assert_called_once_with(100, 200, button="left", clicks=1)

    @patch("time.sleep")
    def test_execute_batch_actions_sleep_parameters(self, mock_sleep):
        """Verify sleep action handles ms, duration_ms, seconds, and delay properly."""
        actions = [
            {"action": "sleep", "duration_ms": 1500},
            {"action": "sleep", "seconds": 0.5},
            {"action": "sleep", "delay": 250},
            {"action": "sleep", "ms": 100},
        ]
        res = execute_batch_actions(actions)
        self.assertTrue(res["success"])
        self.assertEqual(res["executed_count"], 4)
        # Check sleep was called with 1.5, 0.5, 0.25, 0.1 (in addition to settle delays)
        slept_durations = [call.args[0] for call in mock_sleep.call_args_list]
        self.assertIn(1.5, slept_durations)
        self.assertIn(0.5, slept_durations)
        self.assertIn(0.25, slept_durations)
        self.assertIn(0.1, slept_durations)

    # ── 2. Window Snapping Tests ───────────────────────────────────────────────

    def test_get_work_area_returns_valid_bounds(self):
        """Verify get_work_area returns a non-empty 4-tuple of display coordinates."""
        wa = get_work_area(0)
        self.assertEqual(len(wa), 4)
        l, t, r, b = wa
        self.assertGreaterEqual(r, l)
        self.assertGreaterEqual(b, t)

    @unittest.skipUnless(sys.platform == "win32", "Windows-specific snap layout")
    def test_snap_layout_side_by_side(self):
        """Verify snap_layout arranges left and right windows in a single step."""
        with patch("extra.core.platform.windows.focus.find_window_by_title") as mock_find, \
             patch("extra.core.platform.windows.focus.snap_window") as mock_snap:
            mock_win_left = MagicMock()
            mock_win_left.hwnd = 11111
            mock_win_right = MagicMock()
            mock_win_right.hwnd = 22222

            mock_find.side_effect = lambda q, **kwargs: (
                mock_win_left if "paint" in q.lower() else mock_win_right
            )
            mock_snap.return_value = True

            res = snap_layout(layout="side_by_side", left_window="Paint", right_window="Notepad")

            self.assertTrue(res["success"])
            self.assertEqual(res["layout"], "side_by_side")
            self.assertIn("left", res["windows"])
            self.assertIn("right", res["windows"])
            self.assertEqual(mock_snap.call_count, 2)

    @unittest.skipUnless(sys.platform == "win32", "Windows-specific snap layout")
    def test_snap_layout_thirds(self):
        """Verify snap_layout arranges 3 windows into thirds across the screen."""
        with patch("extra.core.platform.windows.focus.find_window_by_title") as mock_find, \
             patch("extra.core.platform.windows.focus.snap_window") as mock_snap:
            mock_calc = MagicMock(hwnd=100)
            mock_paint = MagicMock(hwnd=200)
            mock_notepad = MagicMock(hwnd=300)

            def mock_resolver(q, **kwargs):
                q_low = q.lower()
                if "calc" in q_low:
                    return mock_calc
                elif "paint" in q_low:
                    return mock_paint
                elif "notepad" in q_low:
                    return mock_notepad
                return None

            mock_find.side_effect = mock_resolver
            mock_snap.return_value = True

            res = snap_layout(
                layout="thirds",
                left_window="Calculator",
                center_window="Paint",
                right_window="Notepad",
            )

            self.assertTrue(res["success"])
            self.assertEqual(res["layout"], "thirds")
            self.assertIn("left", res["windows"])
            self.assertIn("center", res["windows"])
            self.assertIn("right", res["windows"])
            self.assertEqual(mock_snap.call_count, 3)

    @unittest.skipUnless(sys.platform == "win32", "Windows-specific snap layout")
    def test_snap_layout_missing_window_reporting(self):
        """Verify snap_layout returns success=False and actionable error when a target window is missing."""
        with patch("extra.core.platform.windows.focus.find_window_by_title") as mock_find, \
             patch("extra.core.platform.windows.focus.snap_window") as mock_snap, \
             patch("extra.core.platform.windows.focus.list_windows") as mock_list:
            mock_win_left = MagicMock()
            mock_win_left.hwnd = 11111

            # Left window found, right window not found
            mock_find.side_effect = lambda q, **kwargs: (
                mock_win_left if "notepad" in q.lower() else None
            )
            mock_snap.return_value = True
            
            mock_w1 = MagicMock()
            mock_w1.title = "Notepad"
            mock_w2 = MagicMock()
            mock_w2.title = "Antigravity IDE"
            mock_list.return_value = [mock_w1, mock_w2]

            res = snap_layout(layout="side_by_side", left_window="Notepad", right_window="NonExistentPaint")

            self.assertFalse(res["success"])
            self.assertIn("error", res)
            self.assertIn("NonExistentPaint", res["error"])
            self.assertIn("available_windows", res)
            self.assertIn("Notepad", res["available_windows"])
            self.assertIn("suggestion", res)

    # ── 3. Batch Filesystem Tests ──────────────────────────────────────────────

    def test_fs_batch_create_tree_and_organize(self):
        """Verify create_tree and organize operations operate accurately on files."""
        # 1. Create directory tree with files
        files_to_create = [
            {"path": "data1.txt", "content": "Hello Text 1"},
            {"path": "data2.csv", "content": "col1,col2\n1,2"},
            {"path": "nested/image.png", "content": "fake_png_data"},
        ]
        create_res = execute_fs_batch(
            operation="create_tree",
            base_dir=self.temp_dir,
            files=files_to_create,
        )
        self.assertTrue(create_res["success"])
        self.assertEqual(create_res["created_count"], 3)
        self.assertTrue((Path(self.temp_dir) / "data1.txt").exists())
        self.assertTrue((Path(self.temp_dir) / "nested" / "image.png").exists())

        # 2. Organize files by extension rules
        rules = {
            "Documents": [".txt"],
            "Spreadsheets": [".csv"],
        }
        org_res = execute_fs_batch(
            operation="organize",
            base_dir=self.temp_dir,
            rules=rules,
        )
        self.assertTrue(org_res["success"])
        self.assertEqual(org_res["moved_count"], 2)
        self.assertTrue((Path(self.temp_dir) / "Documents" / "data1.txt").exists())
        self.assertTrue((Path(self.temp_dir) / "Spreadsheets" / "data2.csv").exists())

    def test_fs_batch_rename_and_delete(self):
        """Verify batch rename and deletion operations."""
        file_a = Path(self.temp_dir) / "orig_a.txt"
        file_a.write_text("orig a", encoding="utf-8")
        file_b = Path(self.temp_dir) / "orig_b.txt"
        file_b.write_text("orig b", encoding="utf-8")

        # 1. Batch rename
        rename_res = execute_fs_batch(
            operation="batch_rename",
            base_dir=self.temp_dir,
            renames=[
                {"old": "orig_a.txt", "new": "renamed_a.txt"},
                {"old": "orig_b.txt", "new": "renamed_b.txt"},
            ],
        )
        self.assertTrue(rename_res["success"])
        self.assertEqual(rename_res["renamed_count"], 2)
        renamed_a = Path(self.temp_dir) / "renamed_a.txt"
        renamed_b = Path(self.temp_dir) / "renamed_b.txt"
        self.assertTrue(renamed_a.exists())
        self.assertTrue(renamed_b.exists())

        # 2. Batch delete
        del_res = execute_fs_batch(
            operation="batch_delete",
            base_dir=self.temp_dir,
            deletes=["renamed_a.txt", "renamed_b.txt"],
        )
        self.assertTrue(del_res["success"])
        self.assertEqual(del_res["deleted_count"], 2)
        self.assertFalse(renamed_a.exists())
        self.assertFalse(renamed_b.exists())

    def test_fs_batch_protected_path_blocking(self):
        """Verify execute_fs_batch blocks operations targeting protected system roots."""
        # 1. Block operations targeting system roots like C:\Windows or bare drive root
        sys_dir = r"C:\Windows" if sys.platform == "win32" else "/etc"
        blocked_res = execute_fs_batch(
            operation="create_tree",
            base_dir=sys_dir,
            files=[{"path": "hack.txt", "content": "blocked"}],
        )
        self.assertFalse(blocked_res["success"])
        self.assertIn("error", blocked_res)
        self.assertIn("protected system path", blocked_res["error"])

        # 2. Block arbitrary deletion of system root paths
        del_sys_res = execute_fs_batch(
            operation="batch_delete",
            base_dir=self.temp_dir,
            deletes=[sys_dir],
        )
        self.assertTrue(del_sys_res["success"])
        self.assertEqual(del_sys_res["deleted_count"], 0)
        self.assertIn("Protected system path blocked", del_sys_res["items"][0]["error"])

    # ── 4. MCP Tools Registration Tests ────────────────────────────────────────

    def test_mcp_tools_registered_on_server(self):
        """Verify all new acceleration tools are registered on the Extra MCP server."""
        tool_names = [t.name for t in server._tool_manager.list_tools()]
        self.assertIn("extra_batch_actions", tool_names)
        self.assertIn("extra_snap_layout", tool_names)
        self.assertIn("extra_fs_batch", tool_names)

    @patch("extra.mcp.server.execute_batch_actions")
    def test_extra_batch_actions_tool_wrapper(self, mock_exec):
        """Verify extra_batch_actions MCP wrapper delegates properly."""
        mock_exec.return_value = {"success": True, "executed_count": 2, "total_duration_ms": 12.5}
        res = extra_batch_actions(actions=[{"action": "sleep", "ms": 10}])
        self.assertTrue(res["success"])
        self.assertEqual(res["executed_count"], 2)


if __name__ == "__main__":
    unittest.main()
