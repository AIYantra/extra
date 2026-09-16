"""Tests for Pillar 5: Phased Multi-Channel Package Ecosystem.

Validates:
1. Phase A: Curl one-liner distribution scripts and public parity.
2. Phase B: Homebrew Tap formula (Formula/extra.rb) specification and helper scripts.
3. Phase C: PyPI universal wheel build (pyproject.toml, build artifacts, CI/CD publish pipeline).
4. Phase D: MCP Registry & Marketplace submissions (server.json, smithery.yaml, glama.json, .cursor/mcp.json).
5. Version synchronization (0.2.0) across all package ecosystem descriptors.
"""

import json
import os
import re
import unittest
from pathlib import Path


class TestPillar5PackageEcosystem(unittest.TestCase):
    """Test suite for Pillar 5 multi-channel distribution channels."""

    def setUp(self):
        self.extra_root = Path(__file__).resolve().parent.parent
        self.expected_version = "0.2.0"

    def test_homebrew_formula_specification(self):
        """Verify Formula/extra.rb meets all Homebrew packaging requirements."""
        formula_path = self.extra_root / "Formula" / "extra.rb"
        self.assertTrue(formula_path.exists(), "Missing Formula/extra.rb")
        content = formula_path.read_text(encoding="utf-8")

        # Class and inheritance
        self.assertIn("class Extra < Formula", content)
        self.assertIn("include Language::Python::Virtualenv", content)

        # Metadata
        self.assertIn('homepage "https://extra.yantraos.com"', content)
        self.assertIn(f"v{self.expected_version}.tar.gz", content)
        self.assertIn('license "MIT"', content)

        # Dependencies
        self.assertIn('depends_on "python@3.12"', content)
        self.assertIn("depends_on :macos => :monterey", content)

        # Virtualenv installation and symlink
        self.assertIn("virtualenv_install_with_resources", content)
        self.assertIn('bin.install_symlink libexec/"bin/extra" => "extra"', content)

        # Post install and doctor test
        self.assertIn('system bin/"extra", "doctor"', content)
        self.assertIn(f'assert_match "extra {self.expected_version}"', content)

    def test_homebrew_tap_helper_script(self):
        """Verify setup_homebrew_tap.sh exists and is valid bash."""
        script_path = self.extra_root / "scripts" / "setup_homebrew_tap.sh"
        self.assertTrue(script_path.exists(), "Missing scripts/setup_homebrew_tap.sh")
        content = script_path.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("#!/usr/bin/env bash"))
        self.assertIn("Formula/extra.rb", content)
        self.assertIn("shasum -a 256", content)

    def test_pyproject_toml_configuration(self):
        """Verify pyproject.toml packaging metadata for extra-desktop."""
        pyproject_path = self.extra_root / "pyproject.toml"
        self.assertTrue(pyproject_path.exists(), "Missing pyproject.toml")
        content = pyproject_path.read_text(encoding="utf-8")

        self.assertIn('name = "extra-desktop"', content)
        self.assertIn(f'version = "{self.expected_version}"', content)
        self.assertIn('extra = "extra.cli:main"', content)

        # Platform-specific dependencies
        self.assertIn("pyobjc-framework-ScreenCaptureKit", content)
        self.assertIn("sys_platform == 'darwin'", content)
        self.assertIn("pywin32", content)
        self.assertIn("sys_platform == 'win32'", content)

    def test_built_wheel_and_sdist_artifacts(self):
        """Verify built wheel and sdist exist and match 0.2.0 release."""
        dist_dir = self.extra_root / "dist"
        expected_wheel = dist_dir / f"extra_desktop-{self.expected_version}-py3-none-any.whl"
        expected_sdist = dist_dir / f"extra_desktop-{self.expected_version}.tar.gz"

        if not expected_wheel.exists() or not expected_sdist.exists():
            import subprocess
            import sys
            subprocess.run(
                [sys.executable, "-m", "build", str(self.extra_root)],
                check=True,
                capture_output=True,
            )

        self.assertTrue(
            expected_wheel.exists(),
            f"Expected universal wheel not found: {expected_wheel}",
        )
        self.assertTrue(
            expected_sdist.exists(),
            f"Expected sdist tarball not found: {expected_sdist}",
        )

        # Verify wheel has nonzero file size
        self.assertGreater(expected_wheel.stat().st_size, 1000)
        self.assertGreater(expected_sdist.stat().st_size, 1000)

    def test_github_actions_workflows(self):
        """Verify CI/CD workflows for cross-platform testing and PyPI releases."""
        workflows_dir = self.extra_root / ".github" / "workflows"
        self.assertTrue(workflows_dir.exists(), "Missing .github/workflows")

        # 1. PyPI Release workflow
        pypi_wf = workflows_dir / "publish-pypi.yml"
        self.assertTrue(pypi_wf.exists(), "Missing publish-pypi.yml")
        pypi_content = pypi_wf.read_text(encoding="utf-8")
        self.assertIn("python -m build", pypi_content)
        self.assertIn("twine upload", pypi_content)
        self.assertIn("action-gh-release", pypi_content)
        self.assertIn("macos-latest", pypi_content)
        self.assertIn("windows-latest", pypi_content)

        # 2. CI workflow
        ci_wf = workflows_dir / "ci.yml"
        self.assertTrue(ci_wf.exists(), "Missing ci.yml")
        ci_content = ci_wf.read_text(encoding="utf-8")
        self.assertIn("macos-latest", ci_content)
        self.assertIn("windows-latest", ci_content)

        # 3. Publish MCP workflow
        mcp_wf = workflows_dir / "publish-mcp.yml"
        self.assertTrue(mcp_wf.exists(), "Missing publish-mcp.yml")
        mcp_content = mcp_wf.read_text(encoding="utf-8")
        self.assertIn("mcp-publisher", mcp_content)

    def test_anthropic_mcp_registry_server_json(self):
        """Verify server.json conforms to official MCP registry schema and version 0.2.0."""
        server_json_path = self.extra_root / "server.json"
        self.assertTrue(server_json_path.exists(), "Missing server.json")
        data = json.loads(server_json_path.read_text(encoding="utf-8"))

        self.assertEqual(data.get("name"), "io.github.AIYantra/extra")
        self.assertEqual(data.get("version"), self.expected_version)
        self.assertIn("macOS", data.get("description", ""))
        # MCP registry strict constraint: description <= 100 characters
        self.assertLessEqual(len(data.get("description", "")), 100)

        packages = data.get("packages", [])
        self.assertGreaterEqual(len(packages), 1)
        pypi_pkg = packages[0]
        self.assertEqual(pypi_pkg.get("registryType"), "pypi")
        self.assertEqual(pypi_pkg.get("identifier"), "extra-desktop")
        self.assertEqual(pypi_pkg.get("version"), self.expected_version)
        self.assertEqual(pypi_pkg.get("transport", {}).get("type"), "stdio")

    def test_smithery_configuration(self):
        """Verify smithery.yaml conforms to Smithery 1-click install specification."""
        smithery_path = self.extra_root / "smithery.yaml"
        self.assertTrue(smithery_path.exists(), "Missing smithery.yaml")
        content = smithery_path.read_text(encoding="utf-8")

        self.assertIn("name: extra", content)
        self.assertIn(f'version: "{self.expected_version}"', content)
        self.assertIn("type: stdio", content)
        self.assertIn("command: extra", content)
        self.assertIn("pip install extra-desktop", content)
        self.assertIn("macos-arm64", content)

    def test_glama_marketplace_manifest(self):
        """Verify glama.json contains required metadata and benchmark citations."""
        glama_path = self.extra_root / "glama.json"
        self.assertTrue(glama_path.exists(), "Missing glama.json")
        data = json.loads(glama_path.read_text(encoding="utf-8"))

        self.assertEqual(data.get("name"), "extra")
        self.assertEqual(data.get("version"), self.expected_version)
        self.assertTrue(data.get("capabilities", {}).get("tools"))

        benchmarks = data.get("benchmarks", {})
        self.assertEqual(benchmarks.get("perception_latency_ms"), 2.4)
        self.assertEqual(benchmarks.get("element_accuracy_percent"), 99.4)

        install = data.get("install", {})
        self.assertIn("install.sh", install.get("macos", ""))
        self.assertIn("install.ps1", install.get("windows", ""))
        self.assertIn("aiyantra/extra", install.get("brew", ""))
        self.assertIn("extra-desktop", install.get("pypi", ""))

    def test_cursor_directory_integration(self):
        """Verify .cursor/mcp.json defines extra server configuration."""
        cursor_path = self.extra_root / ".cursor" / "mcp.json"
        self.assertTrue(cursor_path.exists(), "Missing .cursor/mcp.json")
        data = json.loads(cursor_path.read_text(encoding="utf-8"))

        self.assertIn("mcpServers", data)
        self.assertIn("extra", data["mcpServers"])
        self.assertEqual(data["mcpServers"]["extra"].get("command"), "extra")

    def test_version_synchronization_across_ecosystem(self):
        """Ensure version 0.2.0 is strictly synchronized across all manifests."""
        # pyproject.toml
        pyproject = (self.extra_root / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn(f'version = "{self.expected_version}"', pyproject)

        # Formula/extra.rb
        formula = (self.extra_root / "Formula" / "extra.rb").read_text(encoding="utf-8")
        self.assertIn(f"v{self.expected_version}.tar.gz", formula)
        self.assertIn(f"extra {self.expected_version}", formula)

        # server.json
        server = json.loads((self.extra_root / "server.json").read_text(encoding="utf-8"))
        self.assertEqual(server["version"], self.expected_version)
        self.assertEqual(server["packages"][0]["version"], self.expected_version)

        # smithery.yaml
        smithery = (self.extra_root / "smithery.yaml").read_text(encoding="utf-8")
        self.assertIn(f'version: "{self.expected_version}"', smithery)

        # glama.json
        glama = json.loads((self.extra_root / "glama.json").read_text(encoding="utf-8"))
        self.assertEqual(glama["version"], self.expected_version)


if __name__ == "__main__":
    unittest.main()
