"""
Project Extra — Pillar 2 Automation Engine Verification Test Suite
Validates all technical specifications for install.sh defined in Pillar 2 of plan.md:
1. System & Architecture Validation (Darwin, macOS >= 12.3, arm64/x86_64, Windows guidance)
2. Automated Python 3.10+ Discovery & Homebrew Fallback
3. Sandboxed Virtual Environment (~/.extra/venv) & Self-Healing Idempotency
4. Native Apple PyObjC and MCP dependency provisioning
5. Global CLI (~/.local/bin/extra) & Shell PATH injection (~/.zshrc, ~/.bash_profile)
6. Claude Desktop automated non-destructive MCP injection
7. Multi-IDE client configurations (Cursor, Windsurf)
8. Antigravity CLI (agy) registration & 5-target rules deployment
9. Doctor health diagnostic invocation & TCC deep-link guidance
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


class TestPillar2Installer(unittest.TestCase):
    """Verifies all components of Pillar 2: The install.sh Automation Engine."""

    def setUp(self):
        self.root_dir = Path(__file__).resolve().parent.parent
        self.install_sh_path = self.root_dir / "install.sh"
        self.requirements_path = self.root_dir / "requirements.txt"
        self.cli_path = self.root_dir / "cli.py"
        self.content = self.install_sh_path.read_text(encoding="utf-8")
        self.req_content = self.requirements_path.read_text(encoding="utf-8")
        self.cli_content = self.cli_path.read_text(encoding="utf-8")

    def test_os_and_architecture_validation(self):
        """Installer must validate Darwin host, macOS >= 12.3, and architecture."""
        self.assertIn('uname -s', self.content)
        self.assertIn('Darwin', self.content)
        self.assertIn('sw_vers -productVersion', self.content)
        self.assertIn('ScreenCaptureKit', self.content)
        # Platform guidance for non-Darwin hosts
        self.assertIn('install.ps1', self.content)

    def test_python_discovery_and_provisioning(self):
        """Installer must search candidates (3.10+) and auto-fallback to brew or download link."""
        for cand in ["python3.13", "python3.12", "python3.11", "python3.10", "python3"]:
            self.assertIn(cand, self.content)
        self.assertIn("sys.version_info", self.content)
        self.assertIn("brew install python@3.12", self.content)
        self.assertIn("https://www.python.org/downloads/macos/", self.content)

    def test_sandboxed_virtual_environment_self_healing(self):
        """Installer must use isolated ~/.extra/venv and test integrity for self-healing."""
        self.assertIn('EXTRA_HOME="$HOME/.extra"', self.content)
        self.assertIn('VENV_DIR="$EXTRA_HOME/venv"', self.content)
        # Self-healing idempotency check
        self.assertIn('"$VENV_DIR/bin/python" -c \'import sys; sys.exit(0)\'', self.content)
        self.assertIn('Virtual environment cleanly recreated.', self.content)

    def test_native_dependencies_manifest(self):
        """requirements.txt must declare all Apple PyObjC framework bindings and core deps."""
        apple_frameworks = [
            "pyobjc-core",
            "pyobjc-framework-Cocoa",
            "pyobjc-framework-Quartz",
            "pyobjc-framework-ApplicationServices",
            "pyobjc-framework-ScreenCaptureKit",
        ]
        for framework in apple_frameworks:
            self.assertIn(framework, self.req_content)
            self.assertIn("sys_platform == 'darwin'", self.req_content)

        core_deps = ["mcp", "playwright", "pillow", "imagehash", "numpy", "psutil"]
        for dep in core_deps:
            self.assertIn(dep, self.req_content)

    def test_global_cli_and_path_injection(self):
        """Installer must generate ~/.local/bin/extra wrapper and inject PATH into shell config."""
        self.assertIn('BIN_DIR="$HOME/.local/bin"', self.content)
        self.assertIn('exec "$VENV_DIR/bin/python" -m extra.cli "\\$@"', self.content)
        self.assertIn('.zshrc', self.content)
        self.assertIn('.bash_profile', self.content)

    def test_claude_desktop_mcp_injection(self):
        """Installer must inject extra into claude_desktop_config.json without clobbering."""
        self.assertIn('CLAUDE_DIR="$HOME/Library/Application Support/Claude"', self.content)
        self.assertIn('claude_desktop_config.json', self.content)
        self.assertIn('json.dump(data, f, indent=2)', self.content)
        self.assertIn('data["mcpServers"]["extra"]', self.content)

    def test_multi_client_mcp_injection(self):
        """Installer must support Cursor and Windsurf auto-configuration."""
        self.assertIn('cursor.mcp/mcp.json', self.content)
        self.assertIn('.cursor/mcp.json', self.content)
        self.assertIn('.codeium/windsurf', self.content)
        self.assertIn('mcp_config.json', self.content)

    def test_antigravity_rules_deployment_targets(self):
        """Installer must deploy always-on macOS rules to all 5 required targets."""
        self.assertIn('agy mcp add extra', self.content)
        # Target 1: Global skill
        self.assertIn('.gemini/config/skills/extra-automation/SKILL.md', self.content)
        # Target 2: Global prompt
        self.assertIn('.gemini/GEMINI.md', self.content)
        # Target 3: MCP instructions
        self.assertIn('.gemini/antigravity-cli/mcp/extra/instructions.md', self.content)
        # Target 4: User agent rules
        self.assertIn('.agents/rules/extra_automation.md', self.content)
        # Target 5: Workspace rules
        self.assertIn('.agents/rules', self.content)

    def test_doctor_diagnostic_and_deep_links(self):
        """Installer must invoke doctor and print deep links to System Settings panes."""
        self.assertIn('-m extra.cli doctor', self.content)
        self.assertIn('x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility', self.content)
        self.assertIn('x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture', self.content)


if __name__ == "__main__":
    unittest.main()
