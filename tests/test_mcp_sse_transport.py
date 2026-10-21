"""
Tests for Extra MCP SSE HTTP transport, Bearer authentication middleware,
and ChatGPT Universal Plugin discovery endpoints.
"""

import argparse
import json
import unittest
from starlette.testclient import TestClient

from extra.mcp.server import (
    server,
    BearerAuthASGIMiddleware,
    _PUBLIC_SSE_PATHS,
)
from extra.cli import main as cli_main


class TestMCPSSETransport(unittest.TestCase):
    def setUp(self):
        # Base Starlette app from FastMCP
        self.starlette_app = server.sse_app()
        # Wrapped app with Bearer authentication
        self.test_token = "extra_secret_test_token_2026"
        self.authed_app = BearerAuthASGIMiddleware(self.starlette_app, token=self.test_token)
        self.client = TestClient(self.authed_app)

    def test_root_discovery_endpoint(self):
        """GET / returns service metadata and SSE endpoint."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("name"), "Extra Desktop Operator")
        self.assertEqual(data.get("status"), "online")
        self.assertEqual(data.get("mcp_endpoint"), "/sse")

    def test_health_check_endpoint(self):
        """GET /health returns healthy status."""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertEqual(data.get("version"), "0.3.2")

    def test_plugin_manifest_endpoints(self):
        """GET /plugin.json and /.well-known/ai-plugin.json return compliant OpenAI plugin manifests."""
        for path in ("/plugin.json", "/.well-known/ai-plugin.json"):
            resp = self.client.get(path, headers={"host": "aiyantra.trycloudflare.com"})
            self.assertEqual(resp.status_code, 200, f"Failed on path: {path}")
            manifest = resp.json()
            self.assertEqual(manifest.get("schema_version"), "v1")
            self.assertEqual(manifest.get("name_for_human"), "Extra Desktop Operator")
            self.assertEqual(manifest.get("name_for_model"), "extra_desktop")
            self.assertEqual(manifest.get("auth", {}).get("type"), "service_http")
            self.assertEqual(manifest.get("auth", {}).get("authorization_type"), "bearer")
            
            # Verify SSE transport URL reflects requested host
            openai_ext = manifest.get("extensions", {}).get("com.openai", {})
            mcp_server = openai_ext.get("mcp_server", {})
            self.assertEqual(mcp_server.get("transport"), "sse")
            self.assertIn("aiyantra.trycloudflare.com/sse", mcp_server.get("url"))

            # Verify core tools are declared
            tools = openai_ext.get("tools", [])
            self.assertIn("extra_screenshot", tools)
            self.assertIn("extra_launch", tools)
            self.assertIn("extra_click", tools)
            self.assertIn("extra_type", tools)
            self.assertIn("extra_hotkey", tools)
            self.assertIn("extra_snap_layout", tools)
            self.assertIn("extra_batch_actions", tools)
            self.assertIn("extra_task_complete", tools)

    def test_bearer_auth_protection_on_control_endpoints(self):
        """Protected endpoints return 401 when Bearer token is missing or invalid."""
        # Missing token
        resp = self.client.post("/messages")
        self.assertEqual(resp.status_code, 401)
        self.assertIn("WWW-Authenticate", resp.headers)
        self.assertEqual(resp.headers["WWW-Authenticate"], "Bearer")
        data = resp.json()
        self.assertEqual(data.get("error"), "unauthorized")

        # Invalid token
        resp_invalid = self.client.post("/messages", headers={"Authorization": "Bearer wrong_token"})
        self.assertEqual(resp_invalid.status_code, 401)

    def test_bearer_auth_success_with_header(self):
        """Protected endpoint accepts valid Bearer token in Authorization header."""
        resp = self.client.post(
            "/messages",
            headers={"Authorization": f"Bearer {self.test_token}"},
        )
        # Should bypass 401 and reach MCP handler (which will return 400 for missing session_id)
        self.assertNotEqual(resp.status_code, 401)

    def test_bearer_auth_success_with_query_param(self):
        """Protected endpoint accepts valid token in URL query parameter."""
        resp = self.client.post(
            f"/messages?token={self.test_token}",
        )
        self.assertNotEqual(resp.status_code, 401)

    def test_cors_options_bypass(self):
        """CORS OPTIONS preflight requests bypass authentication."""
        resp = self.client.options("/messages")
        self.assertNotEqual(resp.status_code, 401)

    def test_unified_streamable_http_post_endpoints(self):
        """Unified app handles POST initialize requests on /mcp, /sse, and / seamlessly."""
        from extra.mcp.server import create_unified_mcp_app
        try:
            unified_app = create_unified_mcp_app()
        except ModuleNotFoundError as e:
            self.skipTest(f"FastMCP server dependencies not present: {e}")
            return
        init_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "chatgpt_client", "version": "1.0"},
            },
        }
        headers = {"accept": "application/json, text/event-stream"}
        with TestClient(unified_app) as client:
            for endpoint in ("/mcp", "/sse", "/"):
                resp = client.post(endpoint, json=init_payload, headers=headers)
                self.assertEqual(resp.status_code, 200, f"Failed on endpoint: {endpoint}")
                self.assertIn("2024-11-05", resp.text)


class TestCLIServeParser(unittest.TestCase):
    def test_cli_serve_subcommand_parsing(self):
        """Verifies that 'extra serve' parses arguments accurately."""
        from extra.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["serve", "--port", "8080", "--auth-token", "mysecret", "--tunnel"])
        self.assertEqual(args.command, "serve")
        self.assertEqual(args.port, 8080)
        self.assertEqual(args.auth_token, "mysecret")
        self.assertTrue(args.tunnel)

    def test_cli_run_tunnel_flag(self):
        """Verifies that 'extra run' parses --tunnel flag."""
        from extra.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["run", "--transport", "sse", "--tunnel"])
        self.assertEqual(args.command, "run")
        self.assertEqual(args.transport, "sse")
        self.assertTrue(args.tunnel)


class TestCloudflareTunnel(unittest.TestCase):
    def test_token_generation(self):
        """Generates random 32-character hex tokens."""
        from extra.fastpath.tunnel import generate_secure_token
        tok1 = generate_secure_token()
        tok2 = generate_secure_token()
        self.assertEqual(len(tok1), 32)
        self.assertEqual(len(tok2), 32)
        self.assertNotEqual(tok1, tok2)

    def test_format_chatgpt_banner(self):
        """Validates connection banner formatting."""
        from extra.fastpath.tunnel import format_chatgpt_banner
        banner = format_chatgpt_banner(
            public_url="https://bold-tiger-extra.trycloudflare.com",
            auth_token="test_bearer_token_1234",
            local_port=8080,
        )
        self.assertIn("https://bold-tiger-extra.trycloudflare.com", banner)
        self.assertIn("test_bearer_token_1234", banner)
        self.assertIn("8080", banner)
        self.assertIn("chatgpt.com/plugins", banner)

    def test_find_cloudflared_binary(self):
        """Finds cloudflared executable."""
        import sys
        from unittest.mock import patch
        from extra.fastpath.tunnel import find_cloudflared_binary

        # Check existing system install if present
        bin_path = find_cloudflared_binary()
        if bin_path is not None:
            self.assertTrue(bin_path.exists())

        # Test resolution logic with mocked PATH
        fake_binary = "C:\\Tools\\cloudflared.exe" if sys.platform == "win32" else "/usr/local/bin/cloudflared"
        with patch("shutil.which", return_value=fake_binary):
            resolved = find_cloudflared_binary()
            self.assertIsNotNone(resolved)
            self.assertEqual(str(resolved), fake_binary)


if __name__ == "__main__":
    unittest.main()
