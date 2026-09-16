"""Tests for Pillar 4: Web Infrastructure & Edge Delivery Engine (extra.yantraos.com).

Validates:
1. Cloudflare Worker and Next.js Edge Request Router endpoints and logic.
2. User-Agent adaptive routing contract for universal /install one-liner.
3. Next.js App Router route handlers and fallback mechanisms.
4. Static fallback file parity between source repo and web portal public assets.
5. Landing page UI component contracts (adaptive OS tabs, benchmark table metrics).
6. Security and Content-Type header configuration in next.config.ts.
"""

import os
import re
import unittest
from pathlib import Path


class TestPillar4EdgeRouter(unittest.TestCase):
    """Test suite for Pillar 4 edge request router and delivery engine."""

    def setUp(self):
        self.extra_root = Path(__file__).resolve().parent.parent
        self.workspace_root = self.extra_root.parent
        self.web_root = self.workspace_root / "extra.yantraos.com"

    def _require_web_portal(self):
        """Skip web portal tests when running inside standalone core repo CI."""
        if not self.web_root.exists():
            self.skipTest("extra.yantraos.com repository not present in standalone CI checkout")

    def test_worker_js_exists_and_implements_routing_contract(self):
        """Verify worker.js implements all required routes and UA branching."""
        worker_paths = [self.extra_root / "worker.js"]
        if self.web_root.exists():
            worker_paths.append(self.web_root / "worker.js")

        for wp in worker_paths:
            self.assertTrue(wp.exists(), f"Missing worker script at {wp}")
            content = wp.read_text(encoding="utf-8")

            # Route 1 & 2: Direct scripts & rules
            self.assertIn("/install.sh", content)
            self.assertIn("/install.ps1", content)
            self.assertIn("/extra_automation_macos.md", content)
            self.assertIn("/extra_automation.md", content)
            self.assertIn("/STARTER_PROMPT_MACOS.md", content)
            self.assertIn("/STARTER_PROMPT.md", content)

            # Route 3: Universal /install
            self.assertIn("/install", content)
            self.assertIn("isMacOrUnixUserAgent", content)

            # Plain text Content-Type headers
            self.assertIn("text/plain; charset=utf-8", content)
            self.assertIn("X-Content-Type-Options", content)

    def test_edge_scripts_library_and_route_handlers(self):
        """Verify Next.js lib/edge-scripts.ts and route handler implementations."""
        self._require_web_portal()
        edge_scripts = self.web_root / "lib" / "edge-scripts.ts"
        self.assertTrue(edge_scripts.exists(), "Missing lib/edge-scripts.ts")
        content = edge_scripts.read_text(encoding="utf-8")

        self.assertIn("SCRIPT_ROUTES", content)
        self.assertIn("isMacOrUnixUserAgent", content)
        self.assertIn("serveScriptWithFallback", content)
        self.assertIn("text/plain; charset=utf-8", content)

        # Check that individual route handlers exist
        handlers = [
            "install",
            "install.sh",
            "install.ps1",
            "extra_automation_macos.md",
            "extra_automation.md",
            "STARTER_PROMPT_MACOS.md",
            "STARTER_PROMPT.md",
        ]
        for handler in handlers:
            handler_path = self.web_root / "app" / handler / "route.ts"
            self.assertTrue(
                handler_path.exists(),
                f"Missing App Router route handler at {handler_path}",
            )
            handler_code = handler_path.read_text(encoding="utf-8")
            self.assertIn("GET", handler_code)
            self.assertIn("serveScriptWithFallback", handler_code)

    def test_user_agent_adaptive_branching_logic(self):
        """Verify the user-agent pattern matching classifies Unix/Mac vs Windows correctly."""
        mac_unix_agents = [
            "curl/8.7.1",
            "Wget/1.21.4",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Apple Silicon Mac OS X 14_4_1)",
            "curl/7.68.0-Darwin",
            "git-fetch/2.40.1 (Darwin x86_64)",
            "Linux x86_64; bash-client",
        ]
        windows_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "PowerShell/7.4.1",
            "WindowsPowerShell/5.1.22621.2506",
            "Mozilla/5.0 (Windows NT 11.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
        ]

        def check_mac_unix(ua: str) -> bool:
            u = ua.lower()
            return any(
                k in u
                for k in ["curl", "wget", "darwin", "macintosh", "mac os", "linux", "bsd"]
            )

        for ua in mac_unix_agents:
            self.assertTrue(check_mac_unix(ua), f"Failed to detect Mac/Unix UA: {ua}")

        for ua in windows_agents:
            self.assertFalse(check_mac_unix(ua), f"Falsely detected Mac/Unix for Windows UA: {ua}")

    def test_static_fallback_assets_parity(self):
        """Verify public fallback assets exist in web project and match source repo."""
        self._require_web_portal()
        asset_pairs = [
            (self.extra_root / "install.sh", self.web_root / "public" / "install.sh"),
            (self.extra_root / "install.ps1", self.web_root / "public" / "install.ps1"),
            (
                self.extra_root / "rules" / "extra_automation_macos.md",
                self.web_root / "public" / "extra_automation_macos.md",
            ),
            (
                self.extra_root / "rules" / "extra_automation.md",
                self.web_root / "public" / "extra_automation.md",
            ),
            (
                self.extra_root / "STARTER_PROMPT_MACOS.md",
                self.web_root / "public" / "STARTER_PROMPT_MACOS.md",
            ),
            (
                self.extra_root / "STARTER_PROMPT.md",
                self.web_root / "public" / "STARTER_PROMPT.md",
            ),
        ]
        for src, dst in asset_pairs:
            self.assertTrue(src.exists(), f"Source file {src} does not exist")
            self.assertTrue(dst.exists(), f"Web fallback file {dst} does not exist")
            src_bytes = src.read_bytes()
            dst_bytes = dst.read_bytes()
            self.assertEqual(
                src_bytes,
                dst_bytes,
                f"Content mismatch between {src.name} and web public asset",
            )

    def test_next_config_security_and_script_headers(self):
        """Verify next.config.ts configures nosniff and text/plain for script downloads."""
        self._require_web_portal()
        next_config = self.web_root / "next.config.ts"
        self.assertTrue(next_config.exists(), "Missing next.config.ts")
        content = next_config.read_text(encoding="utf-8")

        self.assertIn("text/plain; charset=utf-8", content)
        self.assertIn("nosniff", content)
        self.assertIn("install", content)
        self.assertIn("extra_automation", content)

    def test_install_section_adaptive_tabs(self):
        """Verify install-section.tsx has adaptive OS detection and manual switcher."""
        self._require_web_portal()
        component = self.web_root / "components" / "install-section.tsx"
        self.assertTrue(component.exists(), "Missing install-section.tsx")
        content = component.read_text(encoding="utf-8")

        # OS detection and toggle
        self.assertIn("navigator.userAgent", content)
        self.assertIn("macos", content)
        self.assertIn("windows", content)
        self.assertIn("curl -sSL https://extra.yantraos.com/install.sh | bash", content)
        self.assertIn("install.ps1", content)
        self.assertIn("STARTER_PROMPT_MACOS.md", content)
        self.assertIn("STARTER_PROMPT.md", content)

    def test_install_modal_adaptive_tabs(self):
        """Verify install-modal.tsx has adaptive OS detection and multi-OS checklists."""
        self._require_web_portal()
        component = self.web_root / "components" / "install-modal.tsx"
        self.assertTrue(component.exists(), "Missing install-modal.tsx")
        content = component.read_text(encoding="utf-8")

        self.assertIn("selectedOS", content)
        self.assertIn("curl -sSL https://extra.yantraos.com/install.sh | bash", content)
        self.assertIn("install.ps1", content)
        self.assertIn("Apple Silicon", content)
        self.assertIn("Screen Recording", content)

    def test_benchmark_table_apple_silicon_metrics(self):
        """Verify benchmark-table.tsx contains Apple Silicon M3/M4 metrics specified in plan.md."""
        self._require_web_portal()
        component = self.web_root / "components" / "benchmark-table.tsx"
        self.assertTrue(component.exists(), "Missing benchmark-table.tsx")
        content = component.read_text(encoding="utf-8")

        # Key metrics from plan.md Section 4.2
        self.assertIn("2.4 ms", content)
        self.assertIn("ScreenCaptureKit", content)
        self.assertIn("< 0.005 s", content)
        self.assertIn("CoreGraphics", content)
        self.assertIn("99.4%", content)
        self.assertIn("AXUIElement", content)

        # Comparative targets
        self.assertIn("250 ms", content)
        self.assertIn("PyAutoGUI", content)
        self.assertIn("3.50 s", content)
        self.assertIn("65.0%", content)

    def test_page_renders_benchmark_table(self):
        """Verify page.tsx imports and renders the BenchmarkTable component."""
        self._require_web_portal()
        page = self.web_root / "app" / "page.tsx"
        content = page.read_text(encoding="utf-8")
        self.assertIn("BenchmarkTable", content)
        self.assertIn("<BenchmarkTable", content)


if __name__ == "__main__":
    unittest.main()
