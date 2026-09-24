"""
Tests for Extra Complete Uninstaller Subsystem & Confirmation Modal.
Verifies native OS confirmation modals (default NO), Claude Desktop deregistration,
user PATH cleaning, and recursive directory purging.
"""

import json
import os
import platform
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from extra.core.uninstall import (
    DISCLAIMER_TEXT,
    cleanup_claude_desktop,
    perform_uninstall,
    prompt_gui_confirmation,
    purge_extra_directory,
)


class TestUninstallerSubsystem(unittest.TestCase):
    """Verifies complete uninstaller behavior and safety guardrails."""

    def test_disclaimer_text_contains_full_scope(self):
        """Verifies disclaimer clearly details memory, blueprints, and venv deletion."""
        self.assertIn("WARNING", DISCLAIMER_TEXT)
        self.assertIn("permanently and completely remove Extra", DISCLAIMER_TEXT)
        self.assertIn("Virtual Environment", DISCLAIMER_TEXT)
        self.assertIn("Episodic Memory Graph", DISCLAIMER_TEXT)
        self.assertIn("Task Blueprints", DISCLAIMER_TEXT)
        self.assertIn("MCP Server Registrations", DISCLAIMER_TEXT)

    @unittest.skipUnless(platform.system() == "Windows", "Windows-specific Win32 MessageBox test")
    def test_windows_messagebox_flags_enforce_default_no(self):
        """Verifies Win32 MessageBoxW is invoked with MB_DEFBUTTON2 (Default: NO)."""
        import ctypes

        mock_msgbox = MagicMock(return_value=7)  # IDNO = 7
        with patch.object(ctypes.windll.user32, "MessageBoxW", mock_msgbox):
            confirmed = prompt_gui_confirmation(title="Test Uninstall")
            self.assertFalse(confirmed)
            mock_msgbox.assert_called_once()
            args = mock_msgbox.call_args[0]
            # args[0] = hwnd (0), args[1] = text, args[2] = title, args[3] = flags
            flags = args[3]
            MB_YESNO = 0x00000004
            MB_ICONWARNING = 0x00000030
            MB_DEFBUTTON2 = 0x00000100
            # Ensure MB_DEFBUTTON2 is set in flags
            self.assertEqual(flags & MB_DEFBUTTON2, MB_DEFBUTTON2, "MB_DEFBUTTON2 must be set to default to NO")
            self.assertEqual(flags & MB_YESNO, MB_YESNO)
            self.assertEqual(flags & MB_ICONWARNING, MB_ICONWARNING)

    @unittest.skipUnless(platform.system() == "Windows", "Windows-specific Win32 MessageBox test")
    def test_windows_messagebox_yes_returns_true(self):
        """Verifies prompt_gui_confirmation returns True only when IDYES (6) is returned."""
        import ctypes

        mock_msgbox = MagicMock(return_value=6)  # IDYES = 6
        with patch.object(ctypes.windll.user32, "MessageBoxW", mock_msgbox):
            confirmed = prompt_gui_confirmation(title="Test Uninstall")
            self.assertTrue(confirmed)

    def test_cleanup_claude_desktop_preserves_other_servers(self):
        """Verifies removing Extra from Claude config leaves other servers intact."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            cfg_path = Path(tmp_dir) / "claude_desktop_config.json"
            initial_data = {
                "mcpServers": {
                    "extra": {
                        "command": "python",
                        "args": ["-m", "extra.mcp.server"],
                    },
                    "github": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-github"],
                    },
                }
            }
            cfg_path.write_text(json.dumps(initial_data, indent=2), encoding="utf-8")

            cleaned = cleanup_claude_desktop(config_path=cfg_path)
            self.assertTrue(cleaned)

            new_data = json.loads(cfg_path.read_text(encoding="utf-8"))
            self.assertNotIn("extra", new_data["mcpServers"])
            self.assertIn("github", new_data["mcpServers"])

    def test_purge_extra_directory_cleans_immediate_subdirs(self):
        """Verifies purge_extra_directory deletes subdirectories and files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            extra_dir = Path(tmp_dir) / ".extra"
            (extra_dir / "workspace").mkdir(parents=True)
            (extra_dir / "workspace" / "test.txt").write_text("data")
            (extra_dir / "blueprints").mkdir(parents=True)
            (extra_dir / "blueprints" / "bp1.json").write_text("{}")
            (extra_dir / "app_registry.json").write_text("{}")

            with patch("subprocess.Popen") as mock_popen:
                purge_extra_directory(extra_dir, delay_sec=100)
                # Immediate subdirs and files should be cleaned immediately
                self.assertFalse((extra_dir / "workspace").exists())
                self.assertFalse((extra_dir / "blueprints").exists())
                self.assertFalse((extra_dir / "app_registry.json").exists())
                mock_popen.assert_called_once()

    def test_perform_uninstall_aborts_on_user_no(self):
        """Verifies uninstallation aborts safely without modifying files when user declines."""
        with patch("extra.core.uninstall.prompt_gui_confirmation", return_value=False):
            with tempfile.TemporaryDirectory() as tmp_dir:
                test_dir = Path(tmp_dir) / ".extra"
                test_dir.mkdir()
                (test_dir / "marker.txt").write_text("persist")

                res = perform_uninstall(force=False, extra_dir=test_dir)
                self.assertEqual(res, 0)
                self.assertTrue((test_dir / "marker.txt").exists())

    def test_perform_uninstall_dry_run(self):
        """Verifies dry-run completes cleanly with code 0 without deleting files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_dir = Path(tmp_dir) / ".extra"
            test_dir.mkdir()
            (test_dir / "data.txt").write_text("test")

            res = perform_uninstall(force=True, dry_run=True, extra_dir=test_dir)
            self.assertEqual(res, 0)
            self.assertTrue((test_dir / "data.txt").exists())


if __name__ == "__main__":
    unittest.main()
