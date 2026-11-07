"""
Project Extra — Form-Fill MCP + Compiler Tests (EXTRA_FORM_FILL_SPEED_RFC Step 6).

Validates the 1-turn form-fill surface without a live browser: the subtask
compiler routes generic fill intents to one attach+fill batch, and the MCP
tools validate args, default to no-submit, and return the guided relaunch
error (never blind clicks) when no CDP endpoint answers. No wall-clock
asserts; the closed-port probe is deterministically refused.
"""

from __future__ import annotations

import socket
import unittest
from unittest.mock import MagicMock, patch

from extra.core.subtask import SubtaskRunner


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class TestFormFillCompiler(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = SubtaskRunner()

    def test_fill_form_with_fields_and_url(self) -> None:
        actions = self.runner.compile_intent("fill form name=Ada email=ada@example.com on example.com")
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["action"], "browser_fill")
        self.assertEqual(actions[0]["fields"], {"name": "Ada", "email": "ada@example.com"})
        self.assertEqual(actions[0]["url_match"], "example.com")
        self.assertFalse(actions[0]["submit"])

    def test_fill_out_login_and_submit(self) -> None:
        actions = self.runner.compile_intent("fill out the login form and submit")
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["action"], "browser_fill")
        self.assertTrue(actions[0]["submit"])

    def test_fill_form_window_qualified_adds_focus(self) -> None:
        actions = self.runner.compile_intent("fill form in Checkout window first=John")
        self.assertEqual(len(actions), 2)
        self.assertEqual(actions[0]["action"], "focus")
        self.assertEqual(actions[0]["window_title"], "Checkout")
        self.assertEqual(actions[1]["action"], "browser_fill")
        self.assertEqual(actions[1]["fields"], {"first": "John"})

    def test_fill_form_bare_compiles_to_snapshot(self) -> None:
        actions = self.runner.compile_intent("fill form")
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["action"], "browser_fill")
        self.assertEqual(actions[0]["fields"], {})

    def test_existing_intents_unaffected(self) -> None:
        calc = self.runner.compile_intent("calculate 12*8=")
        self.assertEqual(calc[0]["action"], "launch")
        note = self.runner.compile_intent("open notepad and type hello")
        self.assertEqual(note[0]["action"], "launch")
        self.assertEqual(self.runner.compile_intent("flibber predicament quark"), [])


class TestFormFillMcp(unittest.TestCase):
    def test_empty_fields_rejected(self) -> None:
        from extra.mcp.server import extra_form_fill

        res = extra_form_fill(fields={})
        self.assertFalse(res["success"])
        self.assertIn("No fields", res["error"])

    def test_no_submit_default_passed_through(self) -> None:
        from extra.mcp import server as srv

        with patch.object(srv, "cdp_fill_form", return_value={"success": True, "filled": ["#a"]}) as mock_fill:
            res = srv.extra_form_fill(fields={"#a": "x"})
        self.assertTrue(res["success"])
        mock_fill.assert_called_once()
        self.assertFalse(mock_fill.call_args.kwargs["submit"])

    def test_submit_true_passed_through(self) -> None:
        from extra.mcp import server as srv

        with patch.object(srv, "cdp_fill_form", return_value={"success": True, "submitted": True}) as mock_fill:
            res = srv.extra_form_fill(fields={"#a": "x"}, submit=True)
        self.assertTrue(res["submitted"])
        self.assertTrue(mock_fill.call_args.kwargs["submit"])

    def test_no_endpoint_returns_guided_error(self) -> None:
        from extra.mcp.server import extra_form_fill

        res = extra_form_fill(fields={"#a": "x"}, port=_free_port())
        self.assertFalse(res["success"])
        self.assertFalse(res.get("attached", False))
        self.assertIn("remediation", res)
        self.assertIn("remote-debugging", res["remediation"])

    def test_sandbox_target_uses_background_browser(self) -> None:
        from extra.mcp import server as srv

        with patch.object(
            srv, "execute_browser_action", return_value={"success": True}
        ) as mock_exec:
            res = srv.extra_form_fill(fields={"#a": "x"}, target="sandbox")
        self.assertTrue(res["success"])
        self.assertEqual(res["target"], "sandbox")
        self.assertEqual(res["filled"], ["#a"])
        mock_exec.assert_called_once_with(action="fill", selector="#a", value="x")

    def test_extra_browser_live_no_endpoint(self) -> None:
        from extra.mcp import server as srv

        with patch.object(srv, "probe_cdp_endpoint", return_value={"open": False, "targets": [], "endpoint": "http://127.0.0.1:1"}):
            res = srv.extra_browser(action="content", target="live", channel="chrome")
        self.assertFalse(res["success"])
        self.assertIn("remediation", res)

    def test_extra_browser_sandbox_default_routes_through(self) -> None:
        from extra.mcp import server as srv

        with patch.object(srv, "execute_browser_action", return_value={"ok": True}) as mock_exec:
            res = srv.extra_browser(action="content")
        mock_exec.assert_called_once_with(action="content", url=None, selector=None, value=None)
        self.assertEqual(res, {"ok": True})

    def test_extra_browser_live_rejects_sandbox_only_actions(self) -> None:
        from extra.mcp import server as srv

        with patch.object(
            srv,
            "probe_cdp_endpoint",
            return_value={"open": True, "targets": [], "endpoint": "http://127.0.0.1:9"},
        ):
            res = srv.extra_browser(action="synthesize_api", target="live")
        self.assertFalse(res["success"])
        self.assertIn("sandbox-only", res["error"])


if __name__ == "__main__":
    unittest.main()
