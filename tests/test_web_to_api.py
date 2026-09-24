"""
Unit tests for Extra Web-to-API & Self-Evolution Subsystem.
Tests CDP sniffer, session vault, code synthesizer, and fastpath crystallization.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from extra.core.scout.cdp_sniffer import CapturedRequest, NetworkSniffer
from extra.core.scout.session_vault import SessionVault, ServiceSession
from extra.core.evolution.api_synthesizer import ApiSynthesizer
from extra.core.evolution.crystallizer import crystallize_skill_evolution
from extra.fastpath.browser import execute_browser_action


class TestWebToApiSubsystem(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_captured_request_filtering(self):
        """Tests that static assets and trackers are filtered while APIs are identified."""
        static_req = CapturedRequest(
            url="https://business.facebook.com/static/style.css",
            method="GET",
            content_type="text/css",
        )
        self.assertFalse(static_req.is_api)
        self.assertFalse(static_req.is_mutation)

        tracker_req = CapturedRequest(
            url="https://www.google-analytics.com/collect",
            method="POST",
            post_data={"event": "pageview"},
        )
        self.assertFalse(tracker_req.is_api)

        api_req = CapturedRequest(
            url="https://business.facebook.com/api/graphql/",
            method="POST",
            headers={"Content-Type": "application/json"},
            post_data={"query": "mutation SchedulePost { ... }"},
            content_type="application/json",
        )
        self.assertTrue(api_req.is_api)
        self.assertTrue(api_req.is_mutation)

    def test_session_vault_redaction_and_assembly(self):
        """Tests safe token redaction and auth header assembly."""
        session = ServiceSession(
            domain="business.facebook.com",
            cookies={"c_user": "100012345678", "xs": "secret_session_token_xyz"},
            auth_headers={"X-FB-LSD": "lsd_token_123", "Authorization": "OAuth token_abc"},
            origin="https://business.facebook.com",
        )

        headers = session.get_request_headers()
        self.assertIn("Cookie", headers)
        self.assertIn("c_user=100012345678", headers["Cookie"])
        self.assertEqual(headers["X-FB-LSD"], "lsd_token_123")

        redacted = session.to_redacted_dict()
        self.assertEqual(redacted["auth_headers"]["Authorization"], "***REDACTED***")
        self.assertIn("...", redacted["cookies_sample"]["xs"])

    def test_session_vault_extract_auth_from_requests(self):
        """Tests extracting CSRF and auth headers from wire traces."""
        req1 = CapturedRequest(
            url="https://business.facebook.com/api/v1/user",
            method="GET",
            headers={"x-fb-lsd": "token_abc", "x-asbd-id": "129487"},
        )
        auth = SessionVault.extract_auth_from_requests([req1], "business.facebook.com")
        self.assertIn("x-fb-lsd", auth)
        self.assertEqual(auth["x-fb-lsd"], "token_abc")

    def test_api_synthesizer_generates_valid_python(self):
        """Tests that ApiSynthesizer generates syntactically valid Python code."""
        req = CapturedRequest(
            url="https://business.facebook.com/api/v1/schedule_post?profile_id=123",
            method="POST",
            headers={"User-Agent": "TestBrowser", "Content-Type": "application/json"},
            post_data={"caption": "Hello world", "scheduled_time": 1790159200},
        )
        session = ServiceSession(
            domain="business.facebook.com",
            cookies={"sessionid": "12345"},
            origin="https://business.facebook.com",
        )

        code = ApiSynthesizer.synthesize_fastpath_module(
            service_name="meta_business",
            action_name="schedule_post",
            captured_request=req,
            session=session,
        )

        self.assertIn("def schedule_post", code)
        self.assertIn("ENDPOINT =", code)
        self.assertIn("httpx.Client", code)
        self.assertIn("__main__", code)

        # Validate python compilation (no SyntaxError)
        compiled = compile(code, "<test_synthesized>", "exec")
        self.assertIsNotNone(compiled)

    def test_api_synthesizer_save_file(self):
        """Tests writing synthesized file to disk."""
        target_dir = Path(self.temp_dir) / "web"
        saved = ApiSynthesizer.save_fastpath_file(
            code="# Test Code\nprint('hello')",
            service_name="test_service",
            target_dir=target_dir,
        )
        self.assertTrue(saved.exists())
        self.assertEqual(saved.name, "test_service.py")
        self.assertEqual(saved.read_text(encoding="utf-8"), "# Test Code\nprint('hello')")

    def test_crystallizer_includes_fastpath_file(self):
        """Tests that crystallize_skill_evolution documents the synthesized fast-path."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            test_target = Path(tmpdir) / "extra-mock_service"
            skill_res = crystallize_skill_evolution(
                app_name="mock_service",
                workflow_summary="Direct API Scheduling",
                instructions="Automates post scheduling directly via GraphQL endpoint.",
                fastpath_file="extra/fastpath/web/mock_service.py",
                target_dirs=[test_target],
            )
            self.assertEqual(skill_res.get("status"), "evolved")
            skill_path = test_target / "SKILL.md"
            self.assertTrue(skill_path.exists())
            content = skill_path.read_text(encoding="utf-8")
            self.assertIn("Evolved API Fast-Path", content)
            self.assertIn("extra/fastpath/web/mock_service.py", content)


    def test_browser_action_dispatch_synthesize(self):
        """Tests browser action dispatcher error handling when no requests were sniffed."""
        res = execute_browser_action(
            action="synthesize_api",
            selector="meta_business",
            value="schedule_post",
        )
        self.assertFalse(res.get("success"))
        self.assertIn("error", res)


if __name__ == "__main__":
    unittest.main()
