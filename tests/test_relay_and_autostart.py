"""
Tests for Extra Background Relay Manager and Windows Autostart Registry Configuration.
"""

import sys
import unittest
from unittest.mock import patch, MagicMock

from extra.relay.manager import RelayManager

if sys.platform == "win32":
    try:
        from extra.core.platform.windows import autostart
    except ImportError:
        autostart = None
else:
    autostart = None


class TestRelayManager(unittest.TestCase):
    def setUp(self):
        # Reset the singleton for isolation
        RelayManager._instance = None

    def test_singleton_instance(self):
        """RelayManager.get_instance() must return identical singleton."""
        mgr1 = RelayManager.get_instance()
        mgr2 = RelayManager.get_instance()
        self.assertIs(mgr1, mgr2)

    def test_initial_status(self):
        """Initial state should be stopped/offline without error."""
        mgr = RelayManager.get_instance()
        status = mgr.get_status()
        self.assertFalse(status["running"])
        self.assertFalse(status["connected"])
        self.assertIn(status["status"], ("stopped", "disabled"))

    def test_local_mode_guard(self):
        """Starting relay without a token or with empty token should gracefully reject."""
        mgr = RelayManager.get_instance()
        success = mgr.start(token="")
        self.assertFalse(success)
        status = mgr.get_status()
        self.assertFalse(status["running"])

    @patch("threading.Thread")
    def test_start_and_stop_lifecycle(self, mock_thread_cls):
        """Starting relay with valid token launches background thread and updates state."""
        mock_thread = MagicMock()
        mock_thread_cls.return_value = mock_thread

        mgr = RelayManager.get_instance()
        success = mgr.start(token="ext_test_valid_relay_token_123")
        self.assertTrue(success)
        self.assertTrue(mgr.is_running())
        self.assertEqual(mgr._status, "connecting")

        # Stop relay gracefully
        stopped = mgr.stop()
        self.assertTrue(stopped)
        self.assertFalse(mgr.is_running())
        self.assertEqual(mgr._status, "stopped")

    def test_ping_disconnected(self):
        """Ping reports connected=False when relay loop is stopped."""
        mgr = RelayManager.get_instance()
        mgr.stop()
        res = mgr.ping()
        self.assertIn("ok", res)
        self.assertFalse(res["connected"])


@unittest.skipUnless(sys.platform == "win32", "Windows autostart tests require Windows")
class TestWindowsAutostart(unittest.TestCase):
    def test_resolve_command(self):
        """Command resolution should return a non-empty string."""
        cmd = autostart._resolve_executable_command()
        self.assertIsInstance(cmd, str)
        self.assertTrue(len(cmd) > 0)

    def test_autostart_info_structure(self):
        """get_autostart_info returns required diagnostic keys."""
        info = autostart.get_autostart_info()
        self.assertIn("supported", info)
        self.assertIn("enabled", info)
        if sys.platform == "win32":
            self.assertTrue(info["supported"])
            self.assertIn("registry_key", info)


class TestUpdatePipeline(unittest.TestCase):
    def test_update_status_structure(self):
        """Verifies run_app get_update_status contract."""
        from pathlib import Path
        import importlib.util

        run_app_path = Path(__file__).resolve().parent.parent / "app" / "run_app.py"
        spec = importlib.util.spec_from_file_location("extra_run_app", run_app_path)
        app_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(app_mod)

        status = app_mod.get_update_status()
        self.assertIsInstance(status, dict)
        self.assertIn("state", status)
        self.assertIn("progress_percent", status)
        self.assertIn("status_text", status)
        self.assertIn("target_version", status)

    def test_update_status_clamping(self):
        """_set_update_status clamps progress percentage between 0 and 100."""
        from pathlib import Path
        import importlib.util

        run_app_path = Path(__file__).resolve().parent.parent / "app" / "run_app.py"
        spec = importlib.util.spec_from_file_location("extra_run_app", run_app_path)
        app_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(app_mod)

        app_mod._set_update_status("downloading", 150, "Testing over 100%")
        st = app_mod.get_update_status()
        self.assertEqual(st["progress_percent"], 100)
        self.assertEqual(st["state"], "downloading")

        app_mod._set_update_status("idle", -20, "Testing negative")
        st = app_mod.get_update_status()
        self.assertEqual(st["progress_percent"], 0)
        self.assertEqual(st["state"], "idle")


if __name__ == "__main__":
    unittest.main()
