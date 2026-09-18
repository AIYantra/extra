"""
Dynamic App Registry & Persistence Tests for Project Extra.
Verifies auto-registration, persistence to ~/.extra/app_registry.json,
cold-start restoration, and window executable discovery.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

if sys.platform != "win32":
    raise unittest.SkipTest("Windows dynamic app registry tests skipped on non-Windows")

from extra.core.platform.windows.shell import (
    APP_REGISTRY,
    BUILTIN_APP_REGISTRY,
    WindowsShellLauncher,
    get_registered_apps,
    get_user_registry_path,
    load_user_registry,
    register_app,
    resolve_executable,
)
from extra.core.platform.macos.shell import (
    MAC_APP_REGISTRY,
    BUILTIN_MAC_APP_REGISTRY,
    MacShellLauncher,
    load_user_registry as load_mac_registry,
    register_app as register_mac_app,
    get_registered_apps as get_mac_registered_apps,
)
from extra.core.platform.windows.focus import get_window_executable_path


class TestAppRegistryDynamic(unittest.TestCase):
    """Test suite for dynamic application auto-registration and disk persistence."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.custom_reg_file = Path(self.temp_dir) / "app_registry.json"

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_builtin_registry_integrity(self):
        """Standard applications must always be present in BUILTIN_APP_REGISTRY."""
        self.assertIn("calc", BUILTIN_APP_REGISTRY)
        self.assertIn("notepad", BUILTIN_APP_REGISTRY)
        self.assertIn("explorer", BUILTIN_APP_REGISTRY)
        self.assertIn("settings", BUILTIN_APP_REGISTRY)
        self.assertIn("calc", APP_REGISTRY)

    def test_register_app_in_memory(self):
        """register_app must update in-memory APP_REGISTRY immediately."""
        test_app = "custom_test_tool"
        success = register_app(
            name=test_app,
            target=r"C:\Tools\custom.exe",
            proc="custom.exe",
            app_type="exe",
            persist=False,
        )
        self.assertTrue(success)
        self.assertIn(test_app, APP_REGISTRY)
        self.assertEqual(APP_REGISTRY[test_app]["target"], r"C:\Tools\custom.exe")
        self.assertEqual(APP_REGISTRY[test_app]["proc"], "custom.exe")

    def test_register_app_persistence(self):
        """register_app with persist=True must write JSON safely to disk."""
        test_app = "persisted_app"
        success = register_app(
            name=test_app,
            target=r"C:\App\test.exe",
            proc="test.exe",
            persist=True,
            custom_path=self.custom_reg_file,
        )
        self.assertTrue(success)
        self.assertTrue(self.custom_reg_file.exists())

        with open(self.custom_reg_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn(test_app, data)
        self.assertEqual(data[test_app]["target"], r"C:\App\test.exe")

    def test_load_user_registry_cold_start(self):
        """load_user_registry must parse disk JSON and populate APP_REGISTRY."""
        fake_reg = {
            "slack_custom": {
                "target": r"C:\Users\test\AppData\Local\slack\slack.exe",
                "type": "exe",
                "proc": "slack.exe",
            },
            "discord_custom": {
                "target": r"C:\Users\test\AppData\Local\Discord\app.exe",
                "type": "exe",
                "proc": "app.exe",
            }
        }
        with open(self.custom_reg_file, "w", encoding="utf-8") as f:
            json.dump(fake_reg, f)

        loaded = load_user_registry(custom_path=self.custom_reg_file)
        self.assertIn("slack_custom", loaded)
        self.assertIn("slack_custom", APP_REGISTRY)
        self.assertEqual(APP_REGISTRY["slack_custom"]["target"], r"C:\Users\test\AppData\Local\slack\slack.exe")

    def test_resolve_executable_auto_registration(self):
        """resolve_executable on an existing file path must auto-register the application."""
        dummy_exe = Path(self.temp_dir) / "dummy_runner.exe"
        dummy_exe.write_text("binary placeholder")

        app_name = "dummy_runner"
        # Ensure not initially in registry
        APP_REGISTRY.pop(app_name, None)

        resolved = resolve_executable(str(dummy_exe), auto_register=True)
        self.assertEqual(resolved, str(dummy_exe))
        self.assertIn(app_name, APP_REGISTRY)
        self.assertEqual(APP_REGISTRY[app_name]["target"], str(dummy_exe))

    def test_get_registered_apps_returns_copy(self):
        """get_registered_apps returns a comprehensive dictionary copy."""
        apps = get_registered_apps()
        self.assertIsInstance(apps, dict)
        self.assertIn("calc", apps)
        # Modifying returned dict must not mutate internal APP_REGISTRY
        apps["temporary_fake_entry"] = {"target": "fake"}
        self.assertNotIn("temporary_fake_entry", APP_REGISTRY)

    def test_macos_registry_symmetry(self):
        """macOS registry must provide symmetric register_app and load_user_registry APIs."""
        self.assertIn("calc", BUILTIN_MAC_APP_REGISTRY)
        mac_reg_file = Path(self.temp_dir) / "mac_registry.json"
        success = register_mac_app(
            name="iterm_custom",
            target="iTerm",
            bundle="/Applications/iTerm.app",
            persist=True,
            custom_path=mac_reg_file,
        )
        self.assertTrue(success)
        self.assertIn("iterm_custom", MAC_APP_REGISTRY)

        loaded = load_mac_registry(custom_path=mac_reg_file)
        self.assertIn("iterm_custom", loaded)

    def test_get_window_executable_path_invalid_hwnd(self):
        """get_window_executable_path must return None safely for invalid HWNDs."""
        self.assertIsNone(get_window_executable_path(0))
        self.assertIsNone(get_window_executable_path(-1))
        self.assertIsNone(get_window_executable_path(999999999))

    def test_windows_shell_launcher_class_interface(self):
        """WindowsShellLauncher must expose register_app and get_registered_apps."""
        launcher = WindowsShellLauncher()
        apps = launcher.get_registered_apps()
        self.assertIn("calc", apps)
        res = launcher.register_app(
            name="test_tool_via_launcher",
            target=r"C:\test\app.exe",
            persist=False,
        )
        self.assertTrue(res)
        self.assertIn("test_tool_via_launcher", launcher.get_registered_apps())


if __name__ == "__main__":
    unittest.main()
