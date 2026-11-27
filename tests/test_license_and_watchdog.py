"""
Tests for Extra CLI online server license verification, persistent device IDs,
and autonomous watchdog telemetry inspection.
"""

import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

from extra.cli import build_parser, cmd_license, cmd_watchdog
from extra.relay.client import get_persistent_device_id


class TestLicenseVerificationAndWatchdog(unittest.TestCase):
    def test_rejects_malformed_license_key(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch("pathlib.Path.home", return_value=Path(tmpdir)):
            rc = cmd_license("EXTRA-FREE-123")
            self.assertEqual(rc, 1)
            self.assertFalse((Path(tmpdir) / ".extra" / "config.json").exists())

    def test_rejects_unissued_key_via_server_verification(self):
        err_stream = io.BytesIO(json.dumps({"success": False, "valid": False, "error": "License key not found"}).encode("utf-8"))
        http_err = urllib.error.HTTPError(
            url="https://extra.yantraos.com/api/license/verify",
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=err_stream,
        )
        with tempfile.TemporaryDirectory() as tmpdir, \
                patch("pathlib.Path.home", return_value=Path(tmpdir)), \
                patch("urllib.request.urlopen", side_effect=http_err):
            rc = cmd_license("EXTRA-PRO-LIFETIME-FAKE-0000-1111-2222")
            self.assertEqual(rc, 1)
            cfg_file = Path(tmpdir) / ".extra" / "config.json"
            if cfg_file.exists():
                cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
                self.assertNotEqual(cfg.get("plan"), "pro")

    def test_accepts_server_verified_key_and_saves_entitlements(self):
        server_payload = {
            "success": True,
            "valid": True,
            "license_key": "EXTRA-PRO-LIFETIME-BFF0-720B-15C3-DDCD",
            "plan": "pro",
            "tier": "Pro Lifetime Tier 1",
            "max_quota": 999999,
            "fleet_limit": 5,
            "paired_devices_count": 1,
            "email": "qa@appsumo.com",
            "relay_token": "extra_rel_verified_test_token",
            "features": ["unlimited_cloud_relay", "chatgpt_phone_bridge", "fleet_5_stations", "watchdog_recovery"],
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(server_payload).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = False

        with tempfile.TemporaryDirectory() as tmpdir, \
                patch("pathlib.Path.home", return_value=Path(tmpdir)), \
                patch("urllib.request.urlopen", return_value=mock_resp):
            rc = cmd_license("EXTRA-PRO-LIFETIME-BFF0-720B-15C3-DDCD")
            self.assertEqual(rc, 0)
            cfg_file = Path(tmpdir) / ".extra" / "config.json"
            self.assertTrue(cfg_file.exists())
            cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
            self.assertEqual(cfg["plan"], "pro")
            self.assertTrue(cfg["server_verified"])
            self.assertEqual(cfg["fleet_limit"], 5)
            self.assertEqual(cfg["relay_token"], "extra_rel_verified_test_token")
            self.assertTrue(str(cfg["device_id"]).startswith("dev_"))

    def test_persistent_device_id_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch("pathlib.Path.home", return_value=Path(tmpdir)):
            d1 = get_persistent_device_id()
            d2 = get_persistent_device_id()
            self.assertTrue(d1.startswith("dev_"))
            self.assertEqual(d1, d2)

    def test_watchdog_cli_subcommand_registered_and_runs(self):
        parser = build_parser()
        args = parser.parse_args(["watchdog"])
        self.assertEqual(args.command, "watchdog")
        with tempfile.TemporaryDirectory() as tmpdir, patch("pathlib.Path.home", return_value=Path(tmpdir)):
            rc = cmd_watchdog(args)
            self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
