"""
Unit and integration tests for Project Extra — Linux Shell Fast-Path Engine
Tests XDG Desktop Entry parsing, indexing, binary resolution, semantic fallback aliases,
and detached application process launching.
"""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from extra.core.platform.base import AbstractShellLauncher, LaunchResult
from extra.core.platform.linux.shell import (
    APP_REGISTRY,
    BROWSER_CANDIDATE_PATHS,
    BUILTIN_APP_FALLBACKS,
    BUILTIN_APP_REGISTRY,
    LinuxShellLauncher,
    ShellLauncher,
    XDGDesktopEntry,
    XDGDesktopIndexer,
    clean_exec_command,
    extract_executable,
    get_desktop_indexer,
    get_registered_apps,
    get_user_registry_path,
    launch_app,
    load_user_registry,
    open_uri,
    register_app,
    resolve_executable,
)


class TestLinuxShellFastPath(unittest.TestCase):
    """Tests for XDG desktop indexing, executable resolution, and launching."""

    def test_abstract_interface_compliance(self):
        launcher = LinuxShellLauncher()
        self.assertIsInstance(launcher, AbstractShellLauncher)
        self.assertIs(ShellLauncher, LinuxShellLauncher)

    def test_clean_exec_command(self):
        cases = [
            ("kate -b %U", "kate -b"),
            ("google-chrome-stable %u", "google-chrome-stable"),
            ("gimp-2.10 %F", "gimp-2.10"),
            ("myapp --icon %i --name %c %k", "myapp --icon --name"),
            ("simple_app", "simple_app"),
            ("nested   spaces   %f  flag", "nested spaces flag"),
        ]
        for raw, expected in cases:
            self.assertEqual(clean_exec_command(raw), expected)

    def test_extract_executable(self):
        self.assertIn("dolphin", extract_executable("dolphin %u"))
        self.assertIn("kate", extract_executable("kate -b %U"))
        self.assertEqual(extract_executable("env BAMF_HINT=test /usr/bin/custom_bin -a"), "/usr/bin/custom_bin")
        self.assertIsNone(extract_executable(""))

    def test_desktop_entry_parser_and_indexer(self):
        # Create a temporary directory with mock .desktop files
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # 1. Valid application
            calc_desktop = tmp_path / "mock-calc.desktop"
            calc_desktop.write_text(
                """[Desktop Entry]
Name=Super Calculator
GenericName=Scientific Calculator
Comment=Perform calculations
Exec=supercalc --gui %u
Icon=calculator
Terminal=false
Type=Application
Categories=Utility;Calculator;
"""
            )

            # 2. Hidden application (should be excluded from general search)
            hidden_desktop = tmp_path / "hidden-app.desktop"
            hidden_desktop.write_text(
                """[Desktop Entry]
Name=Hidden Service
Exec=hiddensvc
Type=Application
NoDisplay=true
"""
            )

            # 3. Non-application type (e.g. Directory or Link)
            dir_desktop = tmp_path / "folder.desktop"
            dir_desktop.write_text(
                """[Desktop Entry]
Name=Folder
Type=Directory
"""
            )

            indexer = XDGDesktopIndexer()
            with patch.object(indexer, "get_search_paths", return_value=[tmp_path]):
                entries = indexer.index(force_refresh=True)
                # Only mock-calc and hidden-app are type Application
                self.assertEqual(len(entries), 2)

                # Search by exact name
                entry = indexer.find_by_query("Super Calculator")
                self.assertIsNotNone(entry)
                self.assertEqual(entry.name, "Super Calculator")
                self.assertEqual(entry.generic_name, "Scientific Calculator")
                self.assertEqual(entry.exec_clean, "supercalc --gui")
                self.assertEqual(entry.executable, "supercalc")
                self.assertIn("Calculator", entry.categories)

                # Search by generic name
                entry_gen = indexer.find_by_query("Scientific Calculator")
                self.assertIsNotNone(entry_gen)
                self.assertEqual(entry_gen.id, "mock-calc.desktop")

                # Search by desktop ID
                entry_id = indexer.find_by_query("mock-calc")
                self.assertIsNotNone(entry_id)

                # Search by category
                calc_cats = indexer.find_by_category("Calculator")
                self.assertEqual(len(calc_cats), 1)
                self.assertEqual(calc_cats[0].id, "mock-calc.desktop")

    def test_builtin_fallback_aliases_configured(self):
        essential_aliases = [
            "calc", "calculator", "notepad", "editor",
            "explorer", "files", "dolphin", "terminal", "konsole",
            "browser", "chrome", "firefox", "settings",
        ]
        for alias in essential_aliases:
            self.assertIn(alias, BUILTIN_APP_FALLBACKS)
            fallback = BUILTIN_APP_FALLBACKS[alias]
            self.assertIn("candidates", fallback)
            self.assertGreater(len(fallback["candidates"]), 0)
            self.assertIn("type", fallback)

    @unittest.skipUnless(sys.platform.startswith("linux"), "Live Linux system test requires Linux host")
    def test_resolve_executable_on_live_system(self):
        # Dolphin or another core tool should be present in full desktop environments
        resolved_files = resolve_executable("files")
        if resolved_files is None:
            self.skipTest("No GUI file manager installed in minimal headless container")
        self.assertIsNotNone(resolved_files)
        target_bin, app_type = resolved_files
        self.assertTrue(Path(target_bin).exists() or shutil_which(target_bin))
        self.assertEqual(app_type, "bin")

        # Browser resolution
        resolved_browser = resolve_executable("browser")
        if resolved_browser is None:
            self.skipTest("No GUI browser installed in minimal headless container")
        self.assertIsNotNone(resolved_browser)
        target_browser, b_type = resolved_browser
        self.assertEqual(b_type, "browser")

    def test_open_uri_dispatch(self):
        with patch("extra.core.platform.linux.shell.subprocess.Popen") as mock_popen:
            with patch("extra.core.platform.linux.shell.shutil.which", return_value="/usr/bin/xdg-open"):
                ok = open_uri("https://yantra.os")
                self.assertTrue(ok)
                mock_popen.assert_called_once()
                args, kwargs = mock_popen.call_args
                self.assertEqual(args[0], ["xdg-open", "https://yantra.os"])
                self.assertTrue(kwargs.get("start_new_session"))

    def test_launch_app_uri_protocol(self):
        with patch("extra.core.platform.linux.shell.open_uri", return_value=True):
            res = launch_app("https://anthropic.com")
            self.assertTrue(res.success)
            self.assertEqual(res.target_executed, "https://anthropic.com")
            self.assertIn("URI dispatched", res.message)

    def test_launch_app_browser_suppression_flags(self):
        with patch("extra.core.platform.linux.shell.resolve_executable", return_value=("/usr/bin/google-chrome-stable", "browser")):
            with patch("extra.core.platform.linux.shell.subprocess.Popen") as mock_popen:
                mock_proc = MagicMock()
                mock_proc.pid = 4321
                mock_popen.return_value = mock_proc

                res = launch_app("chrome", wait_for_window=False)
                self.assertTrue(res.success)
                self.assertEqual(res.pid, 4321)

                mock_popen.assert_called_once()
                args, kwargs = mock_popen.call_args
                cmd = args[0]
                self.assertEqual(cmd[0], "/usr/bin/google-chrome-stable")
                self.assertIn("--no-first-run", cmd)
                self.assertIn("--no-default-browser-check", cmd)
                self.assertIn("--hide-crash-restore-bubble", cmd)
                self.assertTrue(kwargs.get("start_new_session"))

    def test_user_registry_registration_and_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_reg = Path(tmpdir) / "app_reg.json"
            with patch("extra.core.platform.linux.shell.get_user_registry_path", return_value=test_reg):
                ok = register_app("my-custom-tool", "/usr/bin/tool", app_type="bin")
                self.assertTrue(ok)
                self.assertTrue(test_reg.exists())

                data = load_user_registry(custom_path=test_reg)
                self.assertIn("my-custom-tool", data)
                self.assertEqual(data["my-custom-tool"]["target"], "/usr/bin/tool")


def shutil_which(target: str) -> bool:
    import shutil
    return bool(shutil.which(target))


if __name__ == "__main__":
    unittest.main()
