"""
Unit tests for Windows UIPI (User Interface Privilege Isolation) and Token Elevation Guard.
Verifies proactive barrier detection, token inspection, and non-Windows safety fallbacks.
"""

import sys
import unittest

if sys.platform != "win32":
    raise unittest.SkipTest("Windows-only UIPI test suite")

from unittest.mock import patch, MagicMock

from extra.core.platform.windows.uipi import (
    is_current_process_elevated,
    is_window_elevated,
    get_root_window_at_point,
    check_uipi_barrier,
)


class TestWindowsUIPI(unittest.TestCase):
    def test_current_process_elevated_returns_bool(self):
        """is_current_process_elevated must return a boolean without crashing."""
        res = is_current_process_elevated()
        self.assertIsInstance(res, bool)

    def test_invalid_window_handle_returns_false(self):
        """is_window_elevated with invalid or null HWND must return False cleanly."""
        self.assertFalse(is_window_elevated(0))
        self.assertFalse(is_window_elevated(-1))
        self.assertFalse(is_window_elevated(999999999))

    def test_uipi_barrier_none_when_extra_is_elevated(self):
        """When Extra itself is running with Administrator elevation, UIPI never blocks inputs."""
        with patch("extra.core.platform.windows.uipi.is_current_process_elevated", return_value=True):
            res = check_uipi_barrier(hwnd=12345)
            self.assertIsNone(res)

    def test_uipi_barrier_detected_when_target_is_elevated(self):
        """When Extra is standard user and target window is elevated, UIPI barrier must be reported."""
        with patch("extra.core.platform.windows.uipi.is_current_process_elevated", return_value=False), \
             patch("extra.core.platform.windows.uipi.is_window_elevated", return_value=True):
            
            barrier = check_uipi_barrier(hwnd=54321, window_title="PlayAuto EMP")
            self.assertIsNotNone(barrier)
            self.assertTrue(barrier["uipi_barrier"])
            self.assertTrue(barrier["target_elevated"])
            self.assertFalse(barrier["extra_elevated"])
            self.assertIn("Windows UIPI Barrier Detected", barrier["advisory"])
            self.assertIn("PlayAuto EMP", barrier["advisory"])
            self.assertIn("Administrator", barrier["advisory"])

    def test_uipi_barrier_none_when_both_unelevated(self):
        """When target window is also standard user (Medium Integrity), no barrier exists."""
        with patch("extra.core.platform.windows.uipi.is_current_process_elevated", return_value=False), \
             patch("extra.core.platform.windows.uipi.is_window_elevated", return_value=False):
            
            barrier = check_uipi_barrier(hwnd=54321, window_title="Notepad")
            self.assertIsNone(barrier)

    def test_root_window_at_point_safety(self):
        """get_root_window_at_point handles coordinates safely."""
        res = get_root_window_at_point(0, 0)
        # On Windows returns None or int HWND
        self.assertTrue(res is None or isinstance(res, int))

    def test_extra_click_uipi_barrier_interception(self):
        """extra_click must return uipi_barrier=True and advisory when clicking an elevated window without visual change."""
        from extra.mcp.server import extra_click
        from extra.core.platform.base import WindowInfo
        from extra.core.stall_breaker import StallStatus

        fake_fg = WindowInfo(
            hwnd=99999,
            title="PlayAuto EMP",
            class_name="ThunderRT6FormDC",
            process_id=4567,
            process_name="EMP.exe",
            rect=(100, 100, 800, 600),
            is_visible=True,
            is_minimized=False,
        )

        mock_outcome = MagicMock()
        mock_outcome.status = StallStatus.STALLED
        mock_outcome.message = "No visual change detected."
        mock_outcome.strikes = 1
        mock_outcome.recommended_action = None

        with patch("extra.mcp.server.get_foreground_window", return_value=fake_fg), \
             patch("extra.mcp.server.mouse_click"), \
             patch("extra.mcp.server._stall_breaker.evaluate_action", return_value=mock_outcome), \
             patch("extra.core.platform.windows.uipi.is_current_process_elevated", return_value=False), \
             patch("extra.core.platform.windows.uipi.is_window_elevated", return_value=True), \
             patch("extra.mcp.server.distill_screen"):
            
            res = extra_click(x=350, y=250, auto_distill=False)
            self.assertFalse(res["success"])
            self.assertTrue(res.get("uipi_barrier"))
            self.assertEqual(res.get("verification_status"), "blocked_by_uipi")
            self.assertIn("Windows UIPI Barrier Detected", res.get("error", ""))
            self.assertIn("PlayAuto EMP", res.get("error", ""))

    def test_extra_type_uipi_warning(self):
        """extra_type must include uipi_barrier=True warning if foreground window is elevated."""
        from extra.mcp.server import extra_type
        from extra.core.platform.base import WindowInfo

        fake_fg = WindowInfo(
            hwnd=99999,
            title="Administrator: Windows PowerShell",
            class_name="ConsoleWindowClass",
            process_id=1234,
            process_name="powershell.exe",
            rect=(100, 100, 800, 600),
            is_visible=True,
            is_minimized=False,
        )

        with patch("extra.mcp.server.get_foreground_window", return_value=fake_fg), \
             patch("extra.mcp.server.instant_type"), \
             patch("extra.core.platform.windows.uipi.is_current_process_elevated", return_value=False), \
             patch("extra.core.platform.windows.uipi.is_window_elevated", return_value=True):
            
            res = extra_type(text="dir", auto_distill=False)
            self.assertTrue(res.get("uipi_barrier"))
            self.assertIn("Windows UIPI Barrier Detected", res.get("warning", ""))

    def test_relaunch_elevated_quotes_args_with_list2cmdline(self):
        """relaunch_elevated must safely escape quotes and spaces for ShellExecuteW."""
        import ctypes
        from extra.cli import relaunch_elevated

        with patch("extra.core.platform.windows.uipi.is_current_process_elevated", return_value=False), \
             patch("ctypes.windll.shell32.ShellExecuteW", return_value=42) as mock_shell:
            rc = relaunch_elevated(["connect", "--name", 'Workstation "Alpha"', "--hub", "https://example.com"])
            self.assertEqual(rc, 0)
            self.assertTrue(mock_shell.called)
            params_str = mock_shell.call_args[0][3]
            self.assertIn(r'"Workstation \"Alpha\""', params_str)


if __name__ == "__main__":
    unittest.main()
