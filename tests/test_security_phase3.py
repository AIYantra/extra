"""
Unit tests for Phase 3 Security Hardening:
- Workspace Containment & Dotfile Protection in fs.py
- Raw Shell Execution Gating in bridge.py
- Application Allowlist and Environment Scrubbing in cli_harness.py
- Session Desktop Attachment Isolation in geometry.py
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from extra.fastpath.fs import execute_fs_batch, _resolve_safe_dir
from extra.fastpath.bridge import execute_bridge
from extra.fastpath.cli_harness import execute_harness, UniversalHarnessRunner, ALLOWED_HARNESSES


class TestPhase3SecurityFastpath(unittest.TestCase):
    def test_fs_resolve_safe_dir_rejects_bare_home(self):
        """_resolve_safe_dir must reject bare home directory to prevent root directory manipulation."""
        with self.assertRaises(PermissionError):
            _resolve_safe_dir(str(Path.home()))

    def test_fs_create_tree_rejects_dotfiles(self):
        """create_tree must reject creating or modifying hidden dotfiles like .bashrc, .ssh, .env."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_path = Path(tmp_dir) / "workspace"
            base_path.mkdir(parents=True, exist_ok=True)

            res = execute_fs_batch(
                operation="create_tree",
                base_dir=str(base_path),
                files=[
                    {"path": ".bashrc", "content": "malicious export"},
                    {"path": ".ssh/authorized_keys", "content": "ssh-rsa AAAAB3..."},
                    {"path": "safe_dir/.env", "content": "SECRET=1"},
                    {"path": "safe_dir/config.json", "content": "{}"},
                ],
            )
            self.assertTrue(res["success"])
            items = res.get("items", [])
            # Dotfiles must fail
            bashrc_item = next(i for i in items if ".bashrc" in i.get("path", ""))
            self.assertFalse(bashrc_item.get("success"))
            self.assertIn("forbidden", bashrc_item.get("error", "").lower())

            ssh_item = next(i for i in items if "authorized_keys" in i.get("path", ""))
            self.assertFalse(ssh_item.get("success"))

            env_item = next(i for i in items if ".env" in i.get("path", ""))
            self.assertFalse(env_item.get("success"))

            # Legitimate file must succeed
            safe_item = next(i for i in items if "config.json" in i.get("path", ""))
            self.assertTrue(safe_item.get("success"))
            self.assertTrue((base_path / "safe_dir" / "config.json").exists())

    def test_fs_batch_rename_rejects_dotfiles(self):
        """batch_rename must reject renaming a file to a hidden dotfile."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_path = Path(tmp_dir) / "workspace"
            base_path.mkdir(parents=True, exist_ok=True)
            src_file = base_path / "hello.txt"
            src_file.write_text("content", encoding="utf-8")

            res = execute_fs_batch(
                operation="batch_rename",
                base_dir=str(base_path),
                renames=[{"from": "hello.txt", "to": ".hidden_trojan"}],
            )
            self.assertTrue(res["success"])
            item = res["items"][0]
            self.assertFalse(item.get("success"))
            self.assertIn("forbidden", item.get("error", "").lower())
            self.assertTrue(src_file.exists())

    def test_bridge_raw_shell_disabled_by_default(self):
        """Raw shell runtimes (powershell, cmd, bash) must be blocked by default in execute_bridge."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("EXTRA_ENABLE_RAW_SHELL_BRIDGE", None)
            res_ps = execute_bridge(runtime="powershell", payload="Get-Process")
            self.assertFalse(res_ps.success)
            self.assertIn("Security Policy Violation", res_ps.stderr)

            res_cmd = execute_bridge(runtime="cmd", payload="dir")
            self.assertFalse(res_cmd.success)
            self.assertIn("Security Policy Violation", res_cmd.stderr)

    def test_bridge_raw_shell_allowed_with_explicit_flag(self):
        """When EXTRA_ENABLE_RAW_SHELL_BRIDGE=1 is explicitly set, raw shell runtimes execute."""
        if sys.platform != "win32":
            return
        with patch.dict(os.environ, {"EXTRA_ENABLE_RAW_SHELL_BRIDGE": "1"}):
            res_cmd = execute_bridge(runtime="cmd", payload="echo OK_BRIDGE")
            self.assertTrue(res_cmd.success)
            self.assertIn("OK_BRIDGE", res_cmd.stdout)

    def test_cli_harness_blocks_unauthorized_binaries(self):
        """execute_harness must block any binary not in ALLOWED_HARNESSES."""
        runner = UniversalHarnessRunner()
        res_curl = runner.execute(harness="curl", args=["https://example.com"])
        self.assertFalse(res_curl.success)
        self.assertIn("Security Policy Violation", res_curl.stderr)

        res_ps = runner.execute(harness="powershell", args=["-Command", "ls"])
        self.assertFalse(res_ps.success)
        self.assertIn("Security Policy Violation", res_ps.stderr)

    def test_cli_harness_permits_whitelisted_apps(self):
        """Harnesses in ALLOWED_HARNESSES must not be blocked by the allowlist check."""
        runner = UniversalHarnessRunner()
        self.assertIn("blender", ALLOWED_HARNESSES)
        self.assertIn("gimp", ALLOWED_HARNESSES)
        self.assertIn("paint", ALLOWED_HARNESSES)
        # Verify normalization matches allowlist
        slug = runner.normalize_harness_name("cli-anything-blender")
        self.assertIn(slug, ALLOWED_HARNESSES)

    def test_windows_geometry_session_active_check(self):
        """is_current_session_active_console must return a valid boolean on Windows."""
        if sys.platform != "win32":
            return
        from extra.core.platform.windows.geometry import is_current_session_active_console, attach_input_desktop
        is_active = is_current_session_active_console()
        self.assertIsInstance(is_active, bool)
        # Calling attach_input_desktop should not crash
        res = attach_input_desktop()
        self.assertIsInstance(res, bool)


if __name__ == "__main__":
    unittest.main()
