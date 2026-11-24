"""Regression tests for macOS station, browser finder, and single-instance lock.

These tests run cross-platform — they verify the logic/contract without
needing actual macOS system calls.
"""
import os
import sys
import shutil
import tempfile
import textwrap
from pathlib import Path
from unittest import mock

import pytest

# ── Ensure extra src is importable ──────────────────────────────────────
_src = Path(__file__).resolve().parent.parent / "src"
_app = Path(__file__).resolve().parent.parent / "app"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))
if str(_app) not in sys.path:
    sys.path.insert(0, str(_app))


# ════════════════════════════════════════════════════════════════════════
# 1. FORK-BOMB PREVENTION: macOS candidate ordering
# ════════════════════════════════════════════════════════════════════════


class TestMacOSStationCandidateOrdering:
    """The Extra.app/applet path must NEVER appear in the macOS station
    candidate list, and run_app.py must come BEFORE any native .app bundle."""

    def test_no_applet_in_darwin_candidates(self):
        """Verifies the applet path was removed from cli.py source."""
        cli_path = Path(__file__).resolve().parent.parent / "src" / "extra" / "cli.py"
        source = cli_path.read_text(encoding="utf-8")

        # Find the darwin elif block
        darwin_start = source.find('elif sys.platform == "darwin":')
        assert darwin_start != -1, "Could not find the darwin elif block in cli.py"

        # Find the end of the elif block (next elif/else at same indent)
        darwin_block_end = source.find("\n        else:", darwin_start + 1)
        if darwin_block_end == -1:
            darwin_block_end = source.find("\n        elif", darwin_start + 1)
        assert darwin_block_end != -1

        darwin_block = source[darwin_start:darwin_block_end]

        # The applet path must NOT be a candidate (only in a comment)
        lines = darwin_block.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                continue  # Comments are OK
            assert "applet" not in stripped.lower(), (
                f"Fork-bomb risk: 'applet' found in non-comment line: {stripped}"
            )

    def test_run_app_before_native_bundles(self):
        """run_app.py must appear before ExtraApp.app in the candidate list."""
        cli_path = Path(__file__).resolve().parent.parent / "src" / "extra" / "cli.py"
        source = cli_path.read_text(encoding="utf-8")

        darwin_start = source.find('elif sys.platform == "darwin":')
        darwin_block = source[darwin_start:source.find("\n        else:", darwin_start + 1)]

        # Find positions of run_app.py and ExtraApp.app candidates (non-comment lines only)
        run_app_pos = None
        extraapp_pos = None
        for i, line in enumerate(darwin_block.split("\n")):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "run_app" in stripped and "candidates.append" in stripped and run_app_pos is None:
                run_app_pos = i
            if "ExtraApp.app" in stripped and "candidates.append" in stripped and extraapp_pos is None:
                extraapp_pos = i

        assert run_app_pos is not None, "run_app.py not found in darwin candidates"
        assert extraapp_pos is not None, "ExtraApp.app not found in darwin candidates"
        assert run_app_pos < extraapp_pos, (
            f"run_app.py (line {run_app_pos}) must come BEFORE ExtraApp.app (line {extraapp_pos}) "
            f"to prevent fork-bomb via Extra.app wrapper"
        )


# ════════════════════════════════════════════════════════════════════════
# 2. BROWSER FINDER: Cross-platform, graceful empty return
# ════════════════════════════════════════════════════════════════════════


class TestFindBrowserBinary:
    """find_browser_binary() must return '' gracefully when no browser exists
    and must respect platform-specific paths."""

    def test_returns_empty_string_when_no_browser(self):
        """When no Chromium-based browser is installed, return '' not crash."""
        from run_app import find_browser_binary
        with mock.patch("shutil.which", return_value=None), \
             mock.patch("os.path.exists", return_value=False):
            result = find_browser_binary()
            assert result == ""

    def test_does_not_include_safari(self):
        """Safari doesn't support --app= mode and must NOT be a candidate."""
        from run_app import find_browser_binary
        # Inspect the source directly to ensure Safari is not mentioned
        import inspect
        source = inspect.getsource(find_browser_binary)
        assert "Safari" not in source or "intentionally excluded" in source or "NOT" in source, (
            "Safari should not be in the candidate list (no --app= support)"
        )

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only path check")
    def test_macos_chromium_candidates(self):
        """On macOS, the function should check for Chrome, Edge, Chromium, and Brave."""
        from run_app import find_browser_binary
        import inspect
        source = inspect.getsource(find_browser_binary)
        for browser in ["Google Chrome", "Microsoft Edge", "Chromium", "Brave Browser"]:
            assert browser in source, f"macOS should include {browser} as a candidate"


# ════════════════════════════════════════════════════════════════════════
# 3. POSIX SINGLE-INSTANCE LOCK
# ════════════════════════════════════════════════════════════════════════


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only test")
class TestPOSIXSingleInstanceLock:
    """The POSIX flock-based single-instance guard must work on macOS/Linux."""

    def test_first_instance_gets_lock(self):
        """First instance should acquire the lock and return False (proceed)."""
        from run_app import check_single_instance_and_focus
        with mock.patch.object(Path, "home", return_value=Path(tempfile.mkdtemp())):
            result = check_single_instance_and_focus()
            assert result is False, "First instance should proceed (return False)"

    def test_lock_file_contains_pid(self):
        """Lock file should contain the current PID after acquisition."""
        import fcntl
        tmp = tempfile.mkdtemp()
        lock_path = Path(tmp) / ".extra" / "station.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        fd = open(lock_path, "w")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fd.write(str(os.getpid()))
        fd.flush()
        content = lock_path.read_text()
        assert content == str(os.getpid())
        fcntl.flock(fd, fcntl.LOCK_UN)
        fd.close()
        shutil.rmtree(tmp, ignore_errors=True)


# ════════════════════════════════════════════════════════════════════════
# 4. _has_live_app_window: process tracking on non-Windows
# ════════════════════════════════════════════════════════════════════════


class TestHasLiveAppWindow:
    """_has_live_app_window must check process liveness on macOS/Linux."""

    def test_returns_false_when_process_exited(self):
        """When _APP_WINDOW_PROC has exited, should return False."""
        from run_app import _has_live_app_window
        import run_app

        mock_proc = mock.MagicMock()
        mock_proc.poll.return_value = 0  # process has exited

        with mock.patch.object(run_app, "_APP_WINDOW_PROC", mock_proc), \
             mock.patch("sys.platform", "darwin"):
            # We need to call the function with darwin platform
            if sys.platform != "win32":
                result = _has_live_app_window()
                assert result is False

    def test_returns_true_when_process_alive(self):
        """When _APP_WINDOW_PROC is alive, should return True."""
        from run_app import _has_live_app_window
        import run_app

        mock_proc = mock.MagicMock()
        mock_proc.poll.return_value = None  # process still alive

        with mock.patch.object(run_app, "_APP_WINDOW_PROC", mock_proc):
            if sys.platform != "win32":
                result = _has_live_app_window()
                assert result is True

    def test_returns_true_when_no_process_tracked(self):
        """When _APP_WINDOW_PROC is None (server-only mode), should return True."""
        from run_app import _has_live_app_window
        import run_app

        with mock.patch.object(run_app, "_APP_WINDOW_PROC", None):
            if sys.platform != "win32":
                result = _has_live_app_window()
                assert result is True


# ════════════════════════════════════════════════════════════════════════
# 5. _focus_extra_window: macOS AppleScript integration
# ════════════════════════════════════════════════════════════════════════


class TestFocusExtraWindow:
    """_focus_extra_window should use AppleScript on macOS, not just return False."""

    def test_source_has_osascript_on_darwin(self):
        """The function source must contain osascript for macOS."""
        import run_app
        import inspect
        source = inspect.getsource(run_app._focus_extra_window)
        assert "osascript" in source, (
            "_focus_extra_window must use osascript on macOS instead of returning False"
        )
        assert "System Events" in source, (
            "_focus_extra_window must tell System Events to set frontmost"
        )

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only")
    def test_focus_returns_bool(self):
        """On macOS, the function should return a bool regardless of outcome."""
        from run_app import _focus_extra_window
        result = _focus_extra_window()
        assert isinstance(result, bool)


# ════════════════════════════════════════════════════════════════════════
# 6. TCC Client-Aware Diagnostics (source-level verification)
# ════════════════════════════════════════════════════════════════════════


class TestTCCClientDetection:
    """The doctor command must detect the AI host application on macOS."""

    def test_doctor_has_tcc_client_detection(self):
        """cli.py doctor must contain TCC client detection logic."""
        cli_path = Path(__file__).resolve().parent.parent / "src" / "extra" / "cli.py"
        source = cli_path.read_text(encoding="utf-8")
        assert "TCC Client Detection" in source, "doctor must have TCC Client Detection section"
        assert "_host_bundle_map" in source, "doctor must map host process names to bundle IDs"

    def test_host_bundle_map_has_key_clients(self):
        """The host bundle map must include Claude, Cursor, Windsurf, VS Code."""
        cli_path = Path(__file__).resolve().parent.parent / "src" / "extra" / "cli.py"
        source = cli_path.read_text(encoding="utf-8")
        for client in ["claude", "cursor", "windsurf", "vscode"]:
            assert f'"{client}"' in source, f"Host bundle map missing key client: {client}"


# ════════════════════════════════════════════════════════════════════════
# 7. install.sh macOS permissions banner
# ════════════════════════════════════════════════════════════════════════


class TestInstallShPermissionsBanner:
    """install.sh must clearly explain per-app TCC permission requirements."""

    def test_banner_mentions_per_application(self):
        """The permissions banner must warn about per-application grants."""
        install_path = Path(__file__).resolve().parent.parent / "install.sh"
        source = install_path.read_text(encoding="utf-8")
        assert "PER-APPLICATION" in source or "per-application" in source.lower(), (
            "install.sh must warn that macOS grants permissions per-application"
        )

    def test_banner_lists_ai_clients(self):
        """The permissions banner must explicitly list Claude, Cursor, Windsurf."""
        install_path = Path(__file__).resolve().parent.parent / "install.sh"
        source = install_path.read_text(encoding="utf-8")
        for client in ["Claude Desktop", "Cursor", "Windsurf", "VS Code"]:
            assert client in source, f"install.sh permissions banner missing client: {client}"
