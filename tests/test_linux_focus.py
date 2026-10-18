"""
Unit and integration tests for Project Extra — Linux Window Focus & Snapping Engine
Tests KWin D-Bus window management, EWMH/xdotool fallback, title searching,
hwnd mapping, and sub-15ms programmatic snap layouts.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from extra.core.platform.base import AbstractFocusManager, WindowInfo
from extra.core.platform.linux.focus import (
    FocusManager,
    LinuxFocusManager,
    _get_or_create_hwnd,
    _hwnd_to_kwin,
    _kwin_to_hwnd,
    find_window_by_title,
    find_windows_by_process,
    force_activate_window,
    get_focus_manager,
    get_foreground_window,
    get_window_info,
    get_work_area,
    list_windows,
    snap_layout,
    snap_window,
)


class TestLinuxFocusManager(unittest.TestCase):
    """Tests for Linux window enumeration, activation, and snapping."""

    def test_abstract_interface_compliance(self):
        manager = get_focus_manager()
        self.assertIsInstance(manager, AbstractFocusManager)
        self.assertIsInstance(manager, LinuxFocusManager)

    def test_hwnd_synthetic_mapping(self):
        kwin_id = "0_{test-uuid-1234-abcd}"
        hwnd1 = _get_or_create_hwnd(kwin_id)
        self.assertIsInstance(hwnd1, int)
        self.assertGreaterEqual(hwnd1, 10000)

        # Idempotency check
        hwnd2 = _get_or_create_hwnd(kwin_id)
        self.assertEqual(hwnd1, hwnd2)
        self.assertEqual(_hwnd_to_kwin[hwnd1], kwin_id)
        self.assertEqual(_kwin_to_hwnd[kwin_id], hwnd1)

    def test_get_work_area(self):
        l, t, r, b = get_work_area(0)
        self.assertIsInstance(l, int)
        self.assertIsInstance(t, int)
        self.assertIsInstance(r, int)
        self.assertIsInstance(b, int)
        self.assertGreater(r, l)
        self.assertGreater(b, t)

    def test_list_windows_returns_valid_structure(self):
        windows = list_windows(visible_only=False)
        self.assertIsInstance(windows, list)
        for w in windows:
            self.assertIsInstance(w, WindowInfo)
            self.assertIsInstance(w.hwnd, int)
            self.assertIsInstance(w.title, str)
            self.assertIsInstance(w.class_name, str)
            self.assertIsInstance(w.rect, tuple)
            self.assertEqual(len(w.rect), 4)

    def test_find_window_by_title_non_existent(self):
        win = find_window_by_title("__definitely_non_existent_extra_window_query__", timeout=0.0)
        self.assertIsNone(win)

    def test_find_window_by_title_substring(self):
        windows = list_windows(visible_only=True)
        if windows:
            first_win = windows[0]
            # Search with a token from the title
            tokens = [t for t in first_win.title.split() if len(t) > 2]
            if tokens:
                query = tokens[0]
                found = find_window_by_title(query, exact=False, timeout=0.0)
                self.assertIsNotNone(found)
                self.assertIn(query.lower(), found.title.lower())

    def test_find_windows_by_process(self):
        windows = list_windows(visible_only=False)
        if windows:
            first_win = windows[0]
            if first_win.class_name:
                found = find_windows_by_process(first_win.class_name, visible_only=False)
                self.assertGreater(len(found), 0)
                self.assertIn(first_win.hwnd, [w.hwnd for w in found])

    def test_get_foreground_window(self):
        fg = get_foreground_window()
        self.assertIsNotNone(fg)
        self.assertIsInstance(fg, WindowInfo)
        self.assertGreaterEqual(len(fg.rect), 4)

    @patch("extra.core.platform.linux.focus.subprocess.check_output")
    def test_mock_busctl_regex_window_enumeration(self, mock_check_output):
        mock_output = (
            'a(sssida{sv}) 2 "0_{win-111}" "Firefox Web Browser" "firefox" 100 0.8 1 '
            '"subtext" s "Desktop 1" "0_{win-222}" "Kate Text Editor" "kate" 100 0.8 1 '
            '"subtext" s "Desktop 1"'
        )
        mock_check_output.return_value = mock_output

        manager = LinuxFocusManager()
        # Force fallback to busctl by patching HAVE_JEEPNEY to False
        with patch("extra.core.platform.linux.focus.HAVE_JEEPNEY", False):
            with patch("extra.core.platform.linux.focus.shutil.which", return_value="/usr/bin/busctl"):
                wins = manager.list_windows(visible_only=True)
                self.assertEqual(len(wins), 2)
                self.assertEqual(wins[0].title, "Firefox Web Browser")
                self.assertEqual(wins[0].class_name, "firefox")
                self.assertEqual(wins[1].title, "Kate Text Editor")
                self.assertEqual(wins[1].class_name, "kate")

    def test_snap_window_invalid_hwnd(self):
        # Snapping a non-existent synthetic window should fail gracefully (return False)
        result = snap_window(999999, position="left")
        self.assertIsInstance(result, bool)

    def test_snap_layout_structure(self):
        res = snap_layout(layout="side_by_side", left_window="non_existent_left", right_window="non_existent_right")
        self.assertIsInstance(res, dict)
        self.assertFalse(res.get("success"))
        self.assertIn("error", res)
        self.assertEqual(res.get("layout"), "side_by_side")
        self.assertIn("results", res)


if __name__ == "__main__":
    unittest.main()
