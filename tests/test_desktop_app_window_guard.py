import sys
from pathlib import Path
import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows-only desktop window test")

# Add extra app directory to path
app_dir = Path(__file__).resolve().parent.parent / "app"
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

from run_app import _candidate_is_app_window, _has_live_app_window


def test_reject_browser_chrome_branding():
    fake_hwnd = 99999
    # Chrome branding
    assert not _candidate_is_app_window(fake_hwnd, "Extra - Google Chrome")
    assert not _candidate_is_app_window(fake_hwnd, "Extra — Flashless Computer Use - Google Chrome")
    # Edge branding
    assert not _candidate_is_app_window(fake_hwnd, "Extra - Microsoft Edge")
    assert not _candidate_is_app_window(fake_hwnd, "Extra - Personal - Microsoft Edge")
    assert not _candidate_is_app_window(fake_hwnd, "Extra - Edge")


def test_reject_website_titles_and_routes():
    fake_hwnd = 99999
    # Dashboard route
    assert not _candidate_is_app_window(fake_hwnd, "Mission Control Dashboard — Project Extra")
    # Login & Auth routes
    assert not _candidate_is_app_window(fake_hwnd, "Login — Project Extra")
    assert not _candidate_is_app_window(fake_hwnd, "Sign Up — Project Extra")
    assert not _candidate_is_app_window(fake_hwnd, "Forgot Password — Project Extra")
    # Marketing & Documentation routes
    assert not _candidate_is_app_window(fake_hwnd, "Features & Architecture | Extra — Autonomous Desktop Computer Use")
    assert not _candidate_is_app_window(fake_hwnd, "About | Extra by yantraOS — Open-Source Computer Use Protocol")
    assert not _candidate_is_app_window(fake_hwnd, "Pricing — Project Extra | World's First ChatGPT Desktop Operator")


def test_reject_unrelated_substring_matches():
    fake_hwnd = 99999
    assert not _candidate_is_app_window(fake_hwnd, "")
    assert not _candidate_is_app_window(fake_hwnd, "Extranote - Notepad")
    assert not _candidate_is_app_window(fake_hwnd, "Extraordinary Claims - Wikipedia")
    assert not _candidate_is_app_window(fake_hwnd, "Google Search: how to use extra app")


def test_has_live_app_window_when_no_app_running():
    # When app is not running, must return False even if browsers are open
    assert _has_live_app_window() is False


def test_detect_os_edition_uses_winreg_no_powershell():
    src_dir = Path(__file__).resolve().parent.parent / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    from extra.core.platform.windows.child_session import detect_os_edition
    import unittest.mock as mock

    # Mock subprocess.run to verify it is NEVER called on Windows when winreg is available
    with mock.patch("subprocess.run") as mock_subproc:
        edition = detect_os_edition()
        assert edition
        assert "Windows" in edition
        if sys.platform == "win32":
            mock_subproc.assert_not_called()


def test_ensure_windows_integration_sac_compliant():
    from run_app import ensure_windows_integration
    # Must run silently without error or window spawning
    ensure_windows_integration()

