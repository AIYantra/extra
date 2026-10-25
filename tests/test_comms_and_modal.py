"""
Unit and Integration Tests for Project Extra Phase 2:
Communications Fast-Path (Telegram, CF_HDROP clipboard) and Universal Modal Confirmation Gate.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from extra.core.subtask import SubtaskRunner
from extra.fastpath.comms import copy_files_to_clipboard, send_telegram_file
from extra.mcp.server import extra_confirm_modal


class TestCommsAndModal(unittest.TestCase):
    """Test suite for Communications Fast-Path and Universal Modal Confirmation."""

    def setUp(self):
        self.runner = SubtaskRunner()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file = Path(self.temp_dir.name) / "test_deliverable.txt"
        self.test_file.write_text("Test market briefing content", encoding="utf-8")

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    @unittest.skipUnless(sys.platform == "win32", "CF_HDROP clipboard injection requires Windows")
    def test_copy_files_to_clipboard(self):
        """Native file drop injection (CF_HDROP) must succeed for existing files."""
        ok = copy_files_to_clipboard([self.test_file])
        self.assertTrue(ok)

        # On Windows, verify CF_HDROP can be read back
        if sys.platform == "win32":
            try:
                import win32clipboard
                import win32con
                win32clipboard.OpenClipboard()
                try:
                    data = win32clipboard.GetClipboardData(win32con.CF_HDROP)
                    self.assertIn(str(self.test_file.resolve()), data)
                finally:
                    win32clipboard.CloseClipboard()
            except Exception:
                pass

    def test_copy_files_to_clipboard_invalid(self):
        """Non-existent files must return False and not pollute the clipboard."""
        ok = copy_files_to_clipboard([Path("non_existent_file_12345.txt")])
        self.assertFalse(ok)

    def test_subtask_telegram_intent_compilation(self):
        """Telegram file send intents must compile to deterministic 7-action pipelines."""
        # 1. Standard file send to @username
        intent_1 = "send file to @ijhaomi on telegram"
        actions_1 = self.runner.compile_intent(intent_1)
        self.assertEqual(len(actions_1), 7)
        self.assertEqual(actions_1[0]["action"], "launch")
        self.assertEqual(actions_1[0]["app_name"], "tg://resolve?domain=ijhaomi")
        self.assertEqual(actions_1[1]["action"], "focus")
        self.assertEqual(actions_1[1]["window_title"], "Telegram")
        self.assertEqual(actions_1[3]["action"], "hotkey")
        self.assertEqual(actions_1[3]["keys"], ["ctrl", "v"])
        self.assertEqual(actions_1[5]["action"], "hotkey")
        self.assertEqual(actions_1[5]["keys"], ["enter"])

        # 2. Explicit filename
        intent_2 = f"send '{self.test_file.name}' to @ijhaomi on telegram"
        actions_2 = self.runner.compile_intent(intent_2)
        self.assertEqual(len(actions_2), 7)
        self.assertEqual(actions_2[0]["app_name"], "tg://resolve?domain=ijhaomi")

        # 3. Via syntax without @ prefix
        intent_3 = "send file to ijhaomi via telegram"
        actions_3 = self.runner.compile_intent(intent_3)
        self.assertEqual(len(actions_3), 7)
        self.assertEqual(actions_3[0]["app_name"], "tg://resolve?domain=ijhaomi")

    def test_compound_nifty_then_telegram(self):
        """Multi-stage compound pipeline (Nifty gainers + Telegram delivery) must chain seamlessly."""
        intent = "fetch nifty50 gainers and save to notepad then send file to @ijhaomi on telegram"
        actions = self.runner.compile_intent(intent)
        self.assertEqual(len(actions), 10)
        # First stage: Notepad with Nifty 50
        self.assertEqual(actions[0]["action"], "launch")
        self.assertEqual(actions[0]["app_name"], "notepad")
        # Second stage: Telegram delivery
        self.assertEqual(actions[3]["action"], "launch")
        self.assertEqual(actions[3]["app_name"], "tg://resolve?domain=ijhaomi")
        self.assertEqual(actions[6]["keys"], ["ctrl", "v"])
        self.assertEqual(actions[8]["keys"], ["enter"])

    @patch("extra.mcp.server.extra_click_element")
    @patch("extra.mcp.server.extra_hotkey")
    @patch("extra.mcp.server.extra_focus_window")
    def test_extra_confirm_modal_element_actuation(self, mock_focus, mock_hotkey, mock_click):
        """When a target button is resolved in the tree, it must actuate via click."""
        mock_click.return_value = {"success": True}
        res = extra_confirm_modal(action="send", window_title="Telegram")
        self.assertTrue(res["success"])
        self.assertEqual(res["action"], "send")
        self.assertEqual(res["method"], "element_actuation")
        self.assertTrue(res["modal_dismissed"])
        mock_focus.assert_called()
        mock_click.assert_called()
        mock_hotkey.assert_not_called()

    @patch("extra.mcp.server.extra_click_element")
    @patch("extra.mcp.server.extra_hotkey")
    def test_extra_confirm_modal_hotkey_fallback(self, mock_hotkey, mock_click):
        """When no button element is found, it must fall back to hardware Enter (or Esc for dismiss)."""
        mock_click.return_value = {"success": False}
        
        # Test Confirm/Send fallback -> Enter
        res_send = extra_confirm_modal(action="send")
        self.assertTrue(res_send["success"])
        self.assertEqual(res_send["method"], "hotkey_fallback")
        mock_hotkey.assert_called_with(keys=["enter"])

        # Test Dismiss fallback -> Esc
        mock_hotkey.reset_mock()
        res_dismiss = extra_confirm_modal(action="dismiss")
        self.assertTrue(res_dismiss["success"])
        self.assertEqual(res_dismiss["method"], "hotkey_fallback")
        mock_hotkey.assert_called_with(keys=["esc"])


if __name__ == "__main__":
    unittest.main()
