"""
Project Extra — Pillar 3 TCC Permissions Playbook Verification Test Suite
Validates all technical specifications and operational mechanics defined in Pillar 3 of plan.md:
1. Two essential permissions (Accessibility, Screen Recording)
2. 1-Click deep-link openers to System Settings panes
3. Interactive terminal guidance card structure & formatting
4. TCC recovery and reset commands (tccutil mapping)
5. CLI permissions and doctor command integration
"""

from __future__ import annotations

import argparse
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

from extra.core.platform.macos.permissions import (
    CLIENT_BUNDLE_MAP,
    URL_ACCESSIBILITY,
    URL_SCREEN_CAPTURE,
    check_accessibility,
    check_screen_recording,
    get_guidance_card,
    open_accessibility_settings,
    open_all_permissions_settings,
    open_screen_recording_settings,
    reset_permissions,
    verify_all_permissions,
)
from extra.cli import cmd_doctor, cmd_permissions


class TestPillar3TCCPlaybook(unittest.TestCase):
    """Verifies all components of Pillar 3: Apple TCC Permissions Playbook."""

    def setUp(self):
        self.root_dir = Path(__file__).resolve().parent.parent
        self.readme_macos_path = self.root_dir / "README_MACOS.md"

    def test_deep_link_url_schemes(self):
        """URL schemes must match official macOS System Settings panes."""
        self.assertEqual(
            URL_ACCESSIBILITY,
            "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
        )
        self.assertEqual(
            URL_SCREEN_CAPTURE,
            "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"
        )

    def test_client_bundle_mappings(self):
        """Standard AI and terminal clients must map to accurate macOS bundle IDs."""
        self.assertEqual(CLIENT_BUNDLE_MAP["terminal"], "com.apple.Terminal")
        self.assertEqual(CLIENT_BUNDLE_MAP["iterm2"], "com.googlecode.iterm2")
        self.assertEqual(CLIENT_BUNDLE_MAP["claude"], "com.anthropic.claudedesktop")
        self.assertEqual(CLIENT_BUNDLE_MAP["cursor"], "com.todesktop.230313mzl4w4u92")
        self.assertEqual(CLIENT_BUNDLE_MAP["windsurf"], "com.codeium.windsurf")

    def test_guidance_card_structure(self):
        """Interactive guidance card must contain formatted ASCII borders and required instructions."""
        card = get_guidance_card()
        self.assertIn("ACTION REQUIRED: MACOS SECURITY PERMISSIONS", card)
        self.assertIn("Accessibility:", card)
        self.assertIn("Screen Recording:", card)
        self.assertIn("Privacy_Accessibility", card)
        self.assertIn("Privacy_ScreenCapture", card)
        self.assertIn("Toggle ON: Terminal / iTerm2 / Claude Desktop", card)
        self.assertIn("extra doctor", card)
        # Check box drawing characters
        self.assertIn("┌", card)
        self.assertIn("┐", card)
        self.assertIn("└", card)
        self.assertIn("┘", card)

    @patch("extra.core.platform.macos.permissions.platform.system", return_value="Darwin")
    @patch("extra.core.platform.macos.permissions.subprocess.run")
    def test_open_settings_invocations(self, mock_run, mock_sys):
        """open_*_settings functions must invoke macOS 'open' with deep link URLs."""
        self.assertTrue(open_accessibility_settings())
        mock_run.assert_called_with(["open", URL_ACCESSIBILITY], check=True)

        self.assertTrue(open_screen_recording_settings())
        mock_run.assert_called_with(["open", URL_SCREEN_CAPTURE], check=True)

        self.assertTrue(open_all_permissions_settings())

    @patch("extra.core.platform.macos.permissions.platform.system", return_value="Darwin")
    @patch("extra.core.platform.macos.permissions.subprocess.run")
    def test_reset_permissions_execution(self, mock_run, mock_sys):
        """reset_permissions must trigger tccutil for Accessibility and ScreenCapture."""
        mock_res = MagicMock(returncode=0, stderr="")
        mock_run.return_value = mock_res

        ok, log = reset_permissions("Claude")
        self.assertTrue(ok)
        self.assertIn("com.anthropic.claudedesktop", log)
        # Verify 2 tccutil calls
        calls = [c[0][0] for c in mock_run.call_args_list]
        self.assertIn(["tccutil", "reset", "Accessibility", "com.anthropic.claudedesktop"], calls)
        self.assertIn(["tccutil", "reset", "ScreenCapture", "com.anthropic.claudedesktop"], calls)

    @patch("extra.cli.platform.system", return_value="Darwin")
    @patch("extra.core.platform.macos.permissions.check_accessibility", return_value=False)
    @patch("extra.core.platform.macos.permissions.check_screen_recording", return_value=False)
    @patch("builtins.print")
    def test_cli_permissions_check_missing(self, mock_print, mock_sr, mock_ax, mock_sys):
        """'extra permissions check' should return 1 and print guidance card when missing."""
        args = argparse.Namespace(action="check")
        ret = cmd_permissions(args)
        self.assertEqual(ret, 1)

    @patch("extra.cli.platform.system", return_value="Darwin")
    @patch("extra.core.platform.macos.permissions.check_accessibility", return_value=True)
    @patch("extra.core.platform.macos.permissions.check_screen_recording", return_value=True)
    @patch("builtins.print")
    def test_cli_permissions_check_granted(self, mock_print, mock_sr, mock_ax, mock_sys):
        """'extra permissions check' should return 0 when all permissions are granted."""
        args = argparse.Namespace(action="check")
        ret = cmd_permissions(args)
        self.assertEqual(ret, 0)

    def test_documentation_sync(self):
        """README_MACOS.md must document deep links and reset commands."""
        readme_text = self.readme_macos_path.read_text(encoding="utf-8")

        self.assertIn(URL_ACCESSIBILITY, readme_text)
        self.assertIn(URL_SCREEN_CAPTURE, readme_text)
        self.assertIn("tccutil reset Accessibility", readme_text)
        self.assertIn("tccutil reset ScreenCapture", readme_text)


if __name__ == "__main__":
    unittest.main()
