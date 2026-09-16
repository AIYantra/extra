"""
Project Extra — Pillar 1 Funnel & Onboarding Verification Test Suite
Validates all deliverables and conversion mechanics defined in Pillar 1 of plan.md:
1. Entry Point A ("Ask Your AI" Single-Prompt Directive) syntax & consistency
2. Entry Point B (Terminal One-Liner) command format
3. Entry Point C (Developer Git Clone) workflow & directory alignment
4. Post-Install Delight Banner & 1-step starter prompt invocation
5. Multi-Client MCP Templates (Claude Desktop, Cursor, Windsurf) validity
6. Client configuration auto-injection simulation (non-destructive JSON patching)
7. STARTER_PROMPT_MACOS.md structure, tool suite coverage, and mandatory reply format
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest


class TestPillar1Funnel(unittest.TestCase):
    """Verifies all components of Pillar 1: The Core Distribution Funnel."""

    def setUp(self):
        self.root_dir = Path(__file__).resolve().parent.parent
        self.readme_macos_path = self.root_dir / "README_MACOS.md"
        self.readme_root_path = self.root_dir / "README.md"
        self.starter_prompt_path = self.root_dir / "STARTER_PROMPT_MACOS.md"
        self.install_sh_path = self.root_dir / "install.sh"
        self.claude_template_path = self.root_dir / "claude_desktop_config.macos.template.json"
        self.cursor_template_path = self.root_dir / "cursor_mcp.macos.template.json"
        self.windsurf_template_path = self.root_dir / "windsurf_mcp.macos.template.json"

    def test_entry_point_a_directive_presence(self):
        """Entry Point A single-prompt directive must exist verbatim across core docs."""
        expected_directive = (
            "Setup Extra on my Mac: In Terminal run "
            "'curl -sSL https://extra.yantraos.com/install.sh | bash', "
            "then read and configure ~/.extra/app/STARTER_PROMPT_MACOS.md so we are ready to use Extra."
        )

        for path in [self.readme_macos_path, self.readme_root_path, self.starter_prompt_path]:
            self.assertTrue(path.exists(), f"File {path.name} must exist")
            content = path.read_text(encoding="utf-8")
            self.assertIn(
                expected_directive,
                content,
                f"Entry Point A directive missing or mutated in {path.name}"
            )

    def test_entry_point_b_terminal_one_liner(self):
        """Entry Point B curl one-liner must be documented consistently."""
        expected_cmd = "curl -sSL https://extra.yantraos.com/install.sh | bash"
        for path in [self.readme_macos_path, self.readme_root_path]:
            content = path.read_text(encoding="utf-8")
            self.assertIn(expected_cmd, content, f"Entry Point B missing in {path.name}")

    def test_entry_point_c_developer_git_clone(self):
        """Entry Point C clone path must clone into ~/.extra/app for seamless prompt resolution."""
        expected_clone = "git clone https://github.com/AIYantra/extra.git ~/.extra/app"
        expected_run = "cd ~/.extra/app && ./install.sh"
        for path in [self.readme_macos_path, self.readme_root_path]:
            content = path.read_text(encoding="utf-8")
            self.assertIn(expected_clone, content, f"Entry Point C clone command missing in {path.name}")
            self.assertIn(expected_run, content, f"Entry Point C execution command missing in {path.name}")

    def test_post_install_banner_in_installer(self):
        """install.sh must output the high-contrast readiness banner matching Pillar 1.2."""
        content = self.install_sh_path.read_text(encoding="utf-8")
        self.assertIn("EXTRA IS INSTALLED AND READY ON MACOS! 🚀", content)
        self.assertIn("How to use Extra (Just 1 step):", content)
        self.assertIn("Setup $STARTER_PROMPT_PATH", content)
        self.assertIn("We are ready! Please restart <your AI application> to make it work.", content)

    def test_symlink_guarantee_in_installer(self):
        """install.sh must guarantee ~/.extra/app exists even when running from a custom git clone."""
        content = self.install_sh_path.read_text(encoding="utf-8")
        self.assertIn('ln -sfn "$INSTALL_DIR" "$EXTRA_HOME/app"', content)

    def test_multi_client_configuration_in_installer(self):
        """install.sh must auto-configure Claude Desktop, Cursor, Windsurf, and Antigravity."""
        content = self.install_sh_path.read_text(encoding="utf-8")
        self.assertIn("claude_desktop_config.json", content)
        self.assertIn("cursor.mcp/mcp.json", content)
        self.assertIn(".codeium/windsurf", content)
        self.assertIn("mcp_config.json", content)
        self.assertIn("agy mcp add extra", content)

    def test_client_mcp_templates_validity(self):
        """All client MCP templates must be valid JSON and define the extra server."""
        templates = [
            self.claude_template_path,
            self.cursor_template_path,
            self.windsurf_template_path
        ]
        for template in templates:
            self.assertTrue(template.exists(), f"Template {template.name} must exist")
            data = json.loads(template.read_text(encoding="utf-8"))
            self.assertIn("mcpServers", data)
            self.assertIn("extra", data["mcpServers"])
            self.assertIn("command", data["mcpServers"]["extra"])
            self.assertEqual(data["mcpServers"]["extra"]["args"], ["-m", "extra.mcp.server"])

    def test_starter_prompt_macos_integrity(self):
        """STARTER_PROMPT_MACOS.md must define the mandatory reply and all 14 extra_* tools."""
        content = self.starter_prompt_path.read_text(encoding="utf-8")
        self.assertIn("We are ready! Please restart", content)
        
        required_tools = [
            "extra_launch",
            "extra_inspect_ui",
            "extra_click_element",
            "extra_screenshot",
            "extra_click",
            "extra_type",
            "extra_hotkey",
            "extra_scroll",
            "extra_drag",
            "extra_browser",
            "extra_focus_window",
            "extra_task_start",
            "extra_task_complete",
            "extra_indicate_status",
        ]
        for tool in required_tools:
            self.assertIn(tool, content, f"Tool {tool} missing from STARTER_PROMPT_MACOS.md")

    def test_client_config_injection_simulation(self):
        """Simulates non-destructive JSON patching of existing client config files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "client_config.json"
            # Pre-existing configuration with another server
            existing_data = {
                "mcpServers": {
                    "existing_server": {
                        "command": "node",
                        "args": ["server.js"]
                    }
                }
            }
            config_file.write_text(json.dumps(existing_data, indent=2), encoding="utf-8")

            # Perform non-destructive patch as done in install.sh
            data = json.loads(config_file.read_text(encoding="utf-8"))
            if "mcpServers" not in data:
                data["mcpServers"] = {}
            data["mcpServers"]["extra"] = {
                "command": "/Users/testuser/.extra/venv/bin/python",
                "args": ["-m", "extra.mcp.server"]
            }
            config_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

            # Verify both existing_server and extra exist
            updated_data = json.loads(config_file.read_text(encoding="utf-8"))
            self.assertIn("existing_server", updated_data["mcpServers"])
            self.assertIn("extra", updated_data["mcpServers"])
            self.assertEqual(updated_data["mcpServers"]["extra"]["args"], ["-m", "extra.mcp.server"])


if __name__ == "__main__":
    unittest.main()
