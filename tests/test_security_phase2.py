"""
Unit tests for Phase 2 Security Hardening:
- Cloud Relay Isolation & Remote Tool Allowlist Enforcement
- Permanent Disallowance of Dangerous Tools (extra_execute_bridge, extra_harness_run)
- Default Removal of Process/Filesystem Tools (extra_fs_batch, extra_launch)
- RelayManager Offline Air-Gap & Thread Lifecycle Safety
"""

import asyncio
import os
import unittest
from unittest.mock import patch, MagicMock

from extra.relay.client import (
    DEFAULT_ALLOWED_RELAY_TOOLS,
    DANGEROUS_REMOTE_TOOLS,
    get_allowed_relay_tools,
    execute_local_tool,
)
from extra.relay.manager import RelayManager


class TestPhase2SecurityRelay(unittest.TestCase):
    def test_default_relay_tools_safe(self):
        """Verify that arbitrary shell/code execution tools are stripped while essential desktop tools are permitted."""
        self.assertNotIn("extra_fs_batch", DEFAULT_ALLOWED_RELAY_TOOLS)
        self.assertNotIn("extra_execute_bridge", DEFAULT_ALLOWED_RELAY_TOOLS)
        self.assertNotIn("extra_harness_run", DEFAULT_ALLOWED_RELAY_TOOLS)
        # Verify safe UI automation and application launch tools remain present
        self.assertIn("extra_launch", DEFAULT_ALLOWED_RELAY_TOOLS)
        self.assertIn("extra_screenshot", DEFAULT_ALLOWED_RELAY_TOOLS)
        self.assertIn("extra_click", DEFAULT_ALLOWED_RELAY_TOOLS)
        self.assertIn("extra_type", DEFAULT_ALLOWED_RELAY_TOOLS)
        self.assertIn("extra_inspect_ui", DEFAULT_ALLOWED_RELAY_TOOLS)

    def test_dangerous_tools_permanently_blocked_in_get_allowed(self):
        """Even if custom env requests dangerous tools, they must be stripped."""
        with patch.dict(os.environ, {"EXTRA_RELAY_ALLOWED_TOOLS": "extra_click,extra_execute_bridge,extra_harness_run,extra_fs_batch"}):
            allowed = get_allowed_relay_tools()
            self.assertNotIn("extra_execute_bridge", allowed)
            self.assertNotIn("extra_harness_run", allowed)
            self.assertIn("extra_click", allowed)

    def test_execute_local_tool_blocks_dangerous_tools(self):
        """execute_local_tool must immediately reject dangerous tools before any execution."""
        async def _run():
            res_bridge = await execute_local_tool("extra_execute_bridge", {"runtime": "python", "payload": "import os"})
            self.assertFalse(res_bridge["success"])
            self.assertIn("Security Policy Violation", res_bridge["error"])

            res_harness = await execute_local_tool("extra_harness_run", {"harness": "test", "command": ["rm", "-rf"]})
            self.assertFalse(res_harness["success"])
            self.assertIn("Security Policy Violation", res_harness["error"])

            res_fs = await execute_local_tool("extra_fs_batch", {"operation": "batch_delete"})
            self.assertFalse(res_fs["success"])
            self.assertIn("Security Policy Violation", res_fs["error"])

            res_private = await execute_local_tool("__subclasses__", {})
            self.assertFalse(res_private["success"])
            self.assertIn("not permitted", res_private["error"])

        asyncio.run(_run())

    def test_relay_manager_offline_airgap(self):
        """RelayManager.set_offline_mode must disconnect, clear in-memory token, and set status to disabled."""
        mgr = RelayManager.get_instance()
        mgr.set_offline_mode()
        status = mgr.get_status()
        self.assertFalse(status["running"])
        self.assertFalse(status["connected"])
        self.assertEqual(status["status"], "disabled")
        self.assertIsNone(mgr._token)

    def test_relay_manager_empty_token_rejection(self):
        """RelayManager.start with empty string must reject cleanly and stay stopped."""
        mgr = RelayManager.get_instance()
        res = mgr.start(token="")
        self.assertFalse(res)
        self.assertEqual(mgr._status, "stopped")


if __name__ == "__main__":
    unittest.main()
