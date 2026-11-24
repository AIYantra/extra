"""
Unit tests for Extra Pre-Release Hardening Fixes.
Verifies command line escaping for spaced arguments, multi-tier window focus,
and profile parameter handling in the shell launcher.
"""

import sys
import unittest
from unittest.mock import patch, MagicMock

if sys.platform != "win32":
    raise unittest.SkipTest("Windows-specific pre-release fixes skipped on non-Windows")

from extra.core.platform.base import WindowInfo
from extra.core.platform.windows.shell import _format_windows_cmdline_args, launch_app
from extra.core.platform.windows.focus import find_window_by_title


class TestPreReleaseFixes(unittest.TestCase):
    def test_cmdline_escaping_spaced_arguments(self):
        """Tests that arguments with spaces are properly quoted for ShellExecuteW."""
        args = ["--profile-directory=Profile 3", "https://example.com/test page/"]
        clean_args, params = _format_windows_cmdline_args(args)
        
        self.assertEqual(len(clean_args), 2)
        # Verify params is quoted according to Win32 CommandLineToArgvW rules
        self.assertIn('"--profile-directory=Profile 3"', params)
        self.assertIn('"https://example.com/test page/"', params)
        # Crucial: Ensure '3' is not split into an independent token
        self.assertNotIn('Profile 3', params.replace('"--profile-directory=Profile 3"', ''))

    def test_cmdline_escaping_accidental_double_wrapping(self):
        """Tests stripping outer redundant quotes like '"--profile-directory=Profile 3"'."""
        args = ['"--profile-directory=Profile 3"', "'C:\\My Folder\\test.txt'"]
        clean_args, params = _format_windows_cmdline_args(args)

        self.assertEqual(clean_args[0], "--profile-directory=Profile 3")
        self.assertEqual(clean_args[1], "C:\\My Folder\\test.txt")
        self.assertIn('"--profile-directory=Profile 3"', params)
        self.assertNotIn('""', params)

    def test_launch_app_profile_injection(self):
        """Tests that profile parameter is injected into command line arguments."""
        with patch("extra.core.platform.windows.shell.shell32.ShellExecuteW", return_value=42) as mock_shell:
            with patch("extra.core.platform.windows.shell.resolve_executable", return_value="C:\\Program Files\\Google\\Chrome\\chrome.exe"):
                res = launch_app(
                    app_name="chrome",
                    args=["https://business.facebook.com/"],
                    profile="Profile 3",
                    wait_for_window=False,
                )
                self.assertTrue(res.success)
                # Verify ShellExecuteW received profile argument
                call_args = mock_shell.call_args[0]
                params_passed = call_args[3]
                self.assertIn('"--profile-directory=Profile 3"', params_passed)

    def test_multi_tier_window_focus_substring(self):
        """Tests Tier 2 substring matching in find_window_by_title."""
        mock_windows = [
            WindowInfo(hwnd=101, title="Meta Business Suite - Google Chrome", class_name="Chrome_WidgetWin_1",
                       process_id=1234, process_name="chrome.exe", rect=(0,0,100,100), is_visible=True, is_minimized=False),
            WindowInfo(hwnd=102, title="Untitled - Notepad", class_name="Notepad",
                       process_id=5678, process_name="notepad.exe", rect=(0,0,100,100), is_visible=True, is_minimized=False),
        ]
        with patch("extra.core.platform.windows.focus.list_windows", return_value=mock_windows):
            win = find_window_by_title("Meta Business Suite")
            self.assertIsNotNone(win)
            self.assertEqual(win.hwnd, 101)

    def test_multi_tier_window_focus_process_fallback(self):
        """Tests Tier 4 process fallback when tab title has not loaded yet."""
        mock_windows = [
            WindowInfo(hwnd=201, title="New Tab", class_name="Chrome_WidgetWin_1",
                       process_id=1234, process_name="chrome.exe", rect=(0,0,100,100), is_visible=True, is_minimized=False),
        ]
        with patch("extra.core.platform.windows.focus.list_windows", return_value=mock_windows):
            # Querying 'chrome' when title is 'New Tab'
            win = find_window_by_title("chrome")
            self.assertIsNotNone(win)
            self.assertEqual(win.hwnd, 201)

    def test_multi_tier_window_focus_multi_word(self):
        """Tests Tier 3 multi-word matching."""
        mock_windows = [
            WindowInfo(hwnd=301, title="Business Suite Manager | Facebook", class_name="Chrome_WidgetWin_1",
                       process_id=1234, process_name="chrome.exe", rect=(0,0,100,100), is_visible=True, is_minimized=False),
        ]
        with patch("extra.core.platform.windows.focus.list_windows", return_value=mock_windows):
            win = find_window_by_title("Business Suite Facebook")
            self.assertIsNotNone(win)
            self.assertEqual(win.hwnd, 301)

    def test_ghost_stroke_rejection_in_task_complete(self):
        """Tests that extra_task_complete rejects completion if strokes were dispatched with 0 ink."""
        from extra.core.memory.ingest import TaskMemoryRecorder
        from extra.mcp.server import extra_task_complete

        rec = TaskMemoryRecorder(task_name="Drawing test")
        # Add a stroke step where pixels_changed was 0
        rec.record_step(
            tool_name="extra_stroke",
            parameters={"point_count": 50, "button": "left", "pixels_changed": 0, "ink_detected": False},
            duration_ms=100.0,
        )

        with patch("extra.mcp.server.get_active_recorder", return_value=rec):
            res = extra_task_complete(summary="Completed drawing", success=True, play_chime=False)
            self.assertFalse(res["success"])
            self.assertEqual(res["status"], "failed")
            self.assertIn("TASK COMPLETION REJECTED", res["error"])

    def test_verified_stroke_in_task_complete(self):
        """Tests that extra_task_complete succeeds when strokes actually deposited visual ink."""
        from extra.core.memory.ingest import TaskMemoryRecorder
        from extra.mcp.server import extra_task_complete

        rec = TaskMemoryRecorder(task_name="Drawing test")
        rec.record_step(
            tool_name="extra_stroke",
            parameters={"point_count": 50, "button": "left", "pixels_changed": 2500, "ink_detected": True},
            duration_ms=100.0,
        )

        with patch("extra.mcp.server.get_active_recorder", return_value=rec):
            with patch("extra.mcp.server.finish_memory_recording", return_value="mem_123"):
                res = extra_task_complete(summary="Completed drawing", success=True, play_chime=False)
                self.assertTrue(res["success"])
                self.assertIn("Verified", res.get("drawing_verification", ""))
                self.assertIn("2500", res.get("drawing_verification", ""))

    def test_extra_stroke_ghost_stroke_failure(self):
        """Tests that extra_stroke returns success=False when 0 pixels change."""
        from PIL import Image
        from extra.core.platform.base import CaptureResult
        from extra.mcp.server import extra_stroke

        dummy_img = Image.new("RGB", (100, 100), "white")
        cap = CaptureResult(image=dummy_img, width=100, height=100, monitor_index=0, duration_ms=1.0)

        with patch("extra.mcp.server.capture_screen", return_value=cap):
            with patch("extra.mcp.server.mouse_stroke") as mock_stroke:
                res = extra_stroke(points=[[10, 10], [20, 20]], duration=0.1)
                self.assertFalse(res["success"])
                self.assertFalse(res["ink_detected"])
                self.assertEqual(res["pixels_changed"], 0)
                self.assertIn("GHOST STROKE DETECTED", res["error"])

    def test_extra_click_two_strike_failure(self):
        """Tests that consecutive zero-change clicks trigger success=False on strike 2."""
        from PIL import Image
        from extra.core.platform.base import CaptureResult
        from extra.mcp.server import extra_click, _stall_breaker

        _stall_breaker.reset()
        dummy_img = Image.new("RGB", (300, 300), "gray")
        cap = CaptureResult(image=dummy_img, width=300, height=300, monitor_index=0, duration_ms=1.0)

        with patch("extra.mcp.server.capture_screen", return_value=cap):
            with patch("extra.mcp.server.mouse_click"):
                # First click with no visual change -> strike 1 (warning)
                res1 = extra_click(x=100, y=100)
                self.assertTrue(res1["success"])
                self.assertFalse(res1["visual_change"])
                self.assertEqual(res1["strikes"], 1)

                # Second click with no visual change -> strike 2 (stalled)
                res2 = extra_click(x=150, y=150)
                self.assertFalse(res2["success"])
                self.assertFalse(res2["visual_change"])
                self.assertEqual(res2["strikes"], 2)
                self.assertIn("STALL DETECTED", res2["error"])


if __name__ == "__main__":
    unittest.main()
