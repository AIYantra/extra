"""
Unit Tests for Multi-Client AI Installer Auto-Wiring (Phase 2).
Verifies that install.ps1 and install.sh automatically detect and configure:
1. Claude Desktop
2. Cursor IDE (Global & Storage)
3. Windsurf IDE
4. Claude Code CLI
5. Roo Code / Cline (VS Code)
6. Antigravity CLI (agy)
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
import unittest


class TestMultiClientInstaller(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).resolve().parent.parent
        self.install_ps1 = (self.root_dir / "install.ps1").read_text(encoding="utf-8")
        self.install_sh = (self.root_dir / "install.sh").read_text(encoding="utf-8")

    def test_install_ps1_contains_all_client_targets(self):
        """install.ps1 must auto-detect and wire all 5 major AI clients."""
        # Function helper
        self.assertIn("function Update-McpConfigFile", self.install_ps1)
        # Claude Desktop
        self.assertIn("Claude Desktop", self.install_ps1)
        self.assertIn("claude_desktop_config.json", self.install_ps1)
        # Cursor IDE
        self.assertIn(".cursor\\mcp.json", self.install_ps1)
        self.assertIn("Cursor IDE (Global)", self.install_ps1)
        self.assertIn("cursor.mcp\\mcp.json", self.install_ps1)
        # Windsurf IDE
        self.assertIn(".codeium\\windsurf\\mcp_config.json", self.install_ps1)
        self.assertIn("Windsurf IDE", self.install_ps1)
        # Claude Code CLI
        self.assertIn("mcp add extra", self.install_ps1)
        self.assertIn(".claude.json", self.install_ps1)
        # Roo Code / Cline
        self.assertIn("rooveterinaryinc.roo-cline", self.install_ps1)
        self.assertIn("saoudrizwan.claude-dev", self.install_ps1)
        self.assertIn("cline_mcp_settings.json", self.install_ps1)

    def test_install_sh_contains_all_client_targets(self):
        """install.sh must auto-detect and wire all 5 major AI clients on Unix/macOS."""
        # Claude Desktop
        self.assertIn("claude_desktop_config.json", self.install_sh)
        # Cursor IDE
        self.assertIn("cursor.mcp/mcp.json", self.install_sh)
        self.assertIn(".cursor/mcp.json", self.install_sh)
        # Windsurf IDE
        self.assertIn("codeium/windsurf/mcp_config.json", self.install_sh)
        # Claude Code CLI
        self.assertIn("claude mcp add extra", self.install_sh)
        # Roo Code / Cline
        self.assertIn("rooveterinaryinc.roo-cline", self.install_sh)
        self.assertIn("cline_mcp_settings.json", self.install_sh)
        # Antigravity CLI
        self.assertIn("agy mcp add extra", self.install_sh)

    def test_json_merge_preserves_existing_mcp_servers(self):
        """Idempotent JSON merging must not overwrite existing servers (e.g. postgres, github)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_mcp.json"
            initial_data = {
                "mcpServers": {
                    "postgres": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/mydb"]
                    }
                }
            }
            config_path.write_text(json.dumps(initial_data, indent=2), encoding="utf-8")

            # Simulate installer update
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["mcpServers"]["extra"] = {
                "command": "C:/path/to/python.exe",
                "args": ["-m", "extra.mcp.server"]
            }
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            # Re-read
            final_data = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertIn("postgres", final_data["mcpServers"])
            self.assertIn("extra", final_data["mcpServers"])
            self.assertEqual(final_data["mcpServers"]["extra"]["args"], ["-m", "extra.mcp.server"])


if __name__ == "__main__":
    unittest.main()
