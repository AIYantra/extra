"""
Unit tests for Project Extra — macOS Window Focus & Shell Fast-Path Engine
Tests NSWorkspace window management, title searching, AppleScript fallback,
app alias resolution, and launch command formatting without requiring real macOS hardware.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, call, patch

from extra.core.platform.base import AbstractFocusManager, AbstractShellLauncher, WindowInfo
from extra.core.platform.macos.focus import (
    MacFocusManager,
    find_window_by_title,
    find_windows_by_process,
    force_activate_window,
    get_foreground_window,
    get_window_info,
    list_windows,
)
from extra.core.platform.macos.shell import (
    MAC_APP_REGISTRY,
    MacShellLauncher,
    launch_app,
    open_uri,
    resolve_executable,
)


class TestMacOSFocusManager(unittest.TestCase):
    """Tests for macOS window enumeration and activation."""

    def test_abstract_interface_compliance(self):
        manager = MacFocusManager()
        self.assertIsInstance(manager, AbstractFocusManager)

    @patch("extra.core.platform.macos.focus.CG")
    def test_list_windows_filtering(self, mock_cg):
        mock_cg.kCGWindowListOptionOnScreenOnly = 1
        mock_cg.kCGWindowListOptionAll = 0
        mock_cg.kCGWindowListExcludeDesktopElements = 16
        mock_cg.kCGNullWindowID = 0

        # Simulate 3 windows: 1 normal app, 1 menu bar / background (layer != 0), 1 tiny window
        mock_cg.CGWindowListCopyWindowInfo.return_value = [
            {
                "kCGWindowLayer": 0,
                "kCGWindowNumber": 101,
                "kCGWindowName": "Document 1 - TextEdit",
                "kCGWindowOwnerName": "TextEdit",
                "kCGWindowOwnerPID": 1234,
                "kCGWindowBounds": {"X": 100, "Y": 150, "Width": 800, "Height": 600},
                "kCGWindowIsOnscreen": True,
            },
            {
                "kCGWindowLayer": 25,  # Menu bar / system overlay
                "kCGWindowNumber": 102,
                "kCGWindowName": "StatusMenu",
                "kCGWindowOwnerName": "SystemUIServer",
                "kCGWindowOwnerPID": 500,
                "kCGWindowBounds": {"X": 0, "Y": 0, "Width": 100, "Height": 25},
                "kCGWindowIsOnscreen": True,
            },
            {
                "kCGWindowLayer": 0,
                "kCGWindowNumber": 103,
                "kCGWindowName": "OffscreenHelper",
                "kCGWindowOwnerName": "Helper",
                "kCGWindowOwnerPID": 1235,
                "kCGWindowBounds": {"X": 0, "Y": 0, "Width": 2, "Height": 2},
                "kCGWindowIsOnscreen": True,
            },
        ]

        windows = list_windows(visible_only=True)
        self.assertEqual(len(windows), 1)
        w = windows[0]
        self.assertEqual(w.hwnd, 101)
        self.assertEqual(w.title, "Document 1 - TextEdit")
        self.assertEqual(w.process_name, "TextEdit")
        self.assertEqual(w.process_id, 1234)
        self.assertEqual(w.rect, (100, 150, 900, 750))
        self.assertTrue(w.is_visible)

    @patch("extra.core.platform.macos.focus.list_windows")
    def test_find_window_by_title_and_process(self, mock_list):
        mock_list.return_value = [
            WindowInfo(
                hwnd=201,
                title="Calculator",
                class_name="NSWindow",
                process_id=4000,
                process_name="Calculator",
                rect=(0, 0, 300, 400),
                is_visible=True,
                is_minimized=False,
            ),
            WindowInfo(
                hwnd=202,
                title="Untitled - TextEdit",
                class_name="NSWindow",
                process_id=4001,
                process_name="TextEdit.app",
                rect=(100, 100, 600, 500),
                is_visible=True,
                is_minimized=False,
            ),
        ]

        # Test partial title match
        win = find_window_by_title("calc")
        self.assertIsNotNone(win)
        self.assertEqual(win.hwnd, 201)

        # Test process search
        procs = find_windows_by_process("TextEdit")
        self.assertEqual(len(procs), 1)
        self.assertEqual(procs[0].hwnd, 202)

        # Test exact match not matching partial
        self.assertIsNone(find_window_by_title("calc", exact=True))

    @patch("extra.core.platform.macos.focus.get_window_info")
    @patch("extra.core.platform.macos.focus.NSRunningApplication")
    def test_force_activate_window_nsrunningapp(self, mock_nsapp, mock_get_info):
        mock_get_info.return_value = WindowInfo(
            hwnd=301,
            title="Calculator",
            class_name="NSWindow",
            process_id=5000,
            process_name="Calculator",
            rect=(0, 0, 300, 400),
            is_visible=True,
            is_minimized=False,
        )

        mock_app_instance = MagicMock()
        mock_app_instance.activateWithOptions_.return_value = True
        mock_nsapp.runningApplicationWithProcessIdentifier_.return_value = mock_app_instance

        success = force_activate_window(301)
        self.assertTrue(success)
        mock_nsapp.runningApplicationWithProcessIdentifier_.assert_called_once_with(5000)
        mock_app_instance.activateWithOptions_.assert_called_once()

    @patch("extra.core.platform.macos.focus.subprocess.run")
    @patch("extra.core.platform.macos.focus.get_window_info")
    @patch("extra.core.platform.macos.focus.NSRunningApplication")
    def test_force_activate_window_applescript_fallback(
        self, mock_nsapp, mock_get_info, mock_subproc
    ):
        mock_get_info.return_value = WindowInfo(
            hwnd=302,
            title="Preview",
            class_name="NSWindow",
            process_id=5001,
            process_name="Preview",
            rect=(0, 0, 800, 600),
            is_visible=True,
            is_minimized=False,
        )

        # NSRunningApplication fails
        mock_app_instance = MagicMock()
        mock_app_instance.activateWithOptions_.return_value = False
        mock_nsapp.runningApplicationWithProcessIdentifier_.return_value = mock_app_instance

        # AppleScript succeeds
        mock_subproc.return_value = MagicMock(returncode=0)

        success = force_activate_window(302)
        self.assertTrue(success)
        mock_subproc.assert_called_once()
        args = mock_subproc.call_args[0][0]
        self.assertIn("osascript", args[0])
        self.assertIn('tell application "Preview" to activate', args[2])


class TestMacOSShellLauncher(unittest.TestCase):
    """Tests for macOS shell application launcher."""

    def test_abstract_interface_compliance(self):
        launcher = MacShellLauncher()
        self.assertIsInstance(launcher, AbstractShellLauncher)

    def test_resolve_executable_aliases(self):
        self.assertEqual(resolve_executable("calc"), "Calculator")
        self.assertEqual(resolve_executable("notepad"), "TextEdit")
        self.assertEqual(resolve_executable("explorer"), "Finder")
        self.assertEqual(resolve_executable("settings"), "System Settings")
        self.assertEqual(resolve_executable("terminal"), "Terminal")
        self.assertEqual(resolve_executable("paint"), "Preview")
        self.assertEqual(resolve_executable("https://google.com"), "https://google.com")

    @patch("extra.core.platform.macos.shell.subprocess.Popen")
    def test_launch_app_basic(self, mock_popen):
        res = launch_app("calc", wait_for_window=False)
        self.assertTrue(res.success)
        self.assertEqual(res.app_name, "calc")
        mock_popen.assert_called_once_with(["open", "-a", "Calculator"])

    @patch("extra.core.platform.macos.shell.os.path.exists")
    @patch("extra.core.platform.macos.shell.subprocess.Popen")
    def test_launch_app_with_file_and_flags(self, mock_popen, mock_exists):
        # When an arg is a file vs flag
        mock_exists.side_effect = lambda p: p == "/tmp/note.txt"

        res = launch_app("notepad", args=["/tmp/note.txt", "-g"], wait_for_window=False)
        self.assertTrue(res.success)
        mock_popen.assert_called_once_with(
            ["open", "-a", "TextEdit", "/tmp/note.txt", "--args", "-g"]
        )

    @patch("extra.core.platform.macos.shell.subprocess.Popen")
    def test_open_uri(self, mock_popen):
        success = open_uri("https://www.google.com/finance")
        self.assertTrue(success)
        mock_popen.assert_called_once_with(["open", "https://www.google.com/finance"])


if __name__ == "__main__":
    unittest.main()
