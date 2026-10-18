"""
Tests for universal window maximization on launch, Windows 11 Snap Assist interception,
and CF_HTML rich clipboard formatting.
"""

import sys
import unittest
from unittest.mock import MagicMock, patch

if sys.platform != "win32":
    raise unittest.SkipTest("Windows-only launch maximization test suite")

import pytest

from extra.core.platform.base import AbstractInputEngine, AbstractShellLauncher
from extra.core.platform.windows.input_engine import (
    atomic_clipboard_paste,
    format_windows_cf_html,
)
from extra.core.platform.windows.shell import launch_app, _format_windows_cmdline_args


def test_format_windows_cf_html():
    fragment = "<table><tr><td>Area</td><td>Status</td></tr></table>"
    cf_bytes = format_windows_cf_html(fragment)
    assert isinstance(cf_bytes, bytes)
    cf_str = cf_bytes.decode("utf-8")
    assert "Version:0.9" in cf_str
    assert "StartHTML:" in cf_str
    assert "EndHTML:" in cf_str
    assert "<!--StartFragment-->" in cf_str
    assert "<!--EndFragment-->" in cf_str
    assert fragment in cf_str


def test_launch_app_chromium_suppress_flags_includes_maximized():
    with patch("extra.core.platform.windows.shell.shell32.ShellExecuteW", return_value=42) as mock_exec, \
         patch("extra.core.platform.windows.shell.resolve_executable", return_value=r"C:\Program Files\Google\Chrome\Application\chrome.exe"), \
         patch("extra.core.platform.windows.shell.list_windows", return_value=[]), \
         patch("extra.core.platform.windows.shell.ensure_dpi_aware"), \
         patch("extra.core.platform.windows.shell.attach_input_desktop"):

        res = launch_app("chrome", wait_for_window=False)
        assert res.success is True
        # Verify ShellExecuteW received --start-maximized in params
        args, kwargs = mock_exec.call_args
        params = args[3]
        assert "--start-maximized" in params


def test_launch_app_explicit_maximize():
    mock_win = MagicMock()
    mock_win.hwnd = 998877
    mock_win.title = "Test App"
    mock_win.process_name = "test.exe"
    mock_win.process_id = 1234

    call_count = 0
    def mock_list_windows(visible_only=False):
        nonlocal call_count
        call_count += 1
        return [] if call_count <= 2 else [mock_win]

    with patch("extra.core.platform.windows.shell.shell32.ShellExecuteW", return_value=42), \
         patch("extra.core.platform.windows.shell.resolve_executable", return_value=r"C:\Tools\test.exe"), \
         patch("extra.core.platform.windows.shell.list_windows", side_effect=mock_list_windows), \
         patch("extra.core.platform.windows.shell.force_activate_window") as mock_activate, \
         patch("extra.core.platform.windows.focus.snap_window", return_value=True) as mock_snap, \
         patch("extra.core.platform.windows.shell.ensure_dpi_aware"), \
         patch("extra.core.platform.windows.shell.attach_input_desktop"):

        res = launch_app("test_app", wait_for_window=True, timeout=1.0, maximize=True)
        assert res.success is True
        assert res.hwnd == 998877
        mock_activate.assert_called_with(998877)
        mock_snap.assert_called_with(998877, "maximize")


def test_win_up_hotkey_interception():
    from extra.core.platform.windows.input_engine import execute_batch_actions
    mock_fg = MagicMock()
    mock_fg.hwnd = 112233
    mock_fg.title = "Target Window"
    mock_fg.process_name = "target.exe"

    with patch("extra.core.focus.get_foreground_window", return_value=mock_fg), \
         patch("extra.core.platform.windows.focus.get_foreground_window", return_value=mock_fg), \
         patch("extra.core.platform.windows.focus.snap_window", return_value=True) as mock_snap:

        res = execute_batch_actions([{"action": "hotkey", "keys": ["win", "up"]}], auto_settle=False)
        assert res["success"] is True
        executed = res["executed"]
        assert len(executed) >= 1
        assert executed[0].get("intercepted_maximize") is True
        mock_snap.assert_called_with(112233, "maximize")


def test_paste_action_with_html_in_batch():
    from extra.core.platform.windows.input_engine import execute_batch_actions
    with patch("extra.core.platform.windows.input_engine.atomic_clipboard_paste") as mock_paste:
        res = execute_batch_actions([
            {"action": "paste", "text": "hello", "html": "<b>hello</b>"}
        ], auto_settle=False)
        assert res["success"] is True
        mock_paste.assert_called_once_with(text="hello", html="<b>hello</b>")
