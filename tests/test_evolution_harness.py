"""
Tests for Extra Evolution GUI-to-CLI Harness Generator.
Verifies codebase analysis, architecture design, scaffolding,
AST-based SKILL.md generation, and end-to-end synthesis.
"""

import json
import os
import sys
from pathlib import Path
import pytest
from click.testing import CliRunner

from extra.core.evolution.harness_generator import (
    HarnessSynthesizer,
    CodebaseAnalysis,
    ArchitectureDesign,
    _sanitize_name,
    _format_display_name,
)


@pytest.fixture
def mock_software_repo(tmp_path: Path) -> Path:
    """Creates a synthetic multi-language software codebase for testing."""
    repo = tmp_path / "mock_editor"
    repo.mkdir()

    # Python backend
    (repo / "main.py").write_text("print('Editor Started')", encoding="utf-8")
    (repo / "editor_core.py").write_text("""
def create_layer(name):
    return {'layer': name}

def render_scene(layers):
    return 'rendered'
""", encoding="utf-8")

    # Data configs
    (repo / "config.json").write_text('{"version": "1.0", "theme": "dark"}', encoding="utf-8")
    (repo / "palette.xml").write_text('<palette><color>#ff0000</color></palette>', encoding="utf-8")

    # C++ plugin
    src = repo / "src"
    src.mkdir()
    (src / "renderer.cpp").write_text("#include <iostream>\nint main() { return 0; }", encoding="utf-8")
    (src / "renderer.hpp").write_text("#pragma once", encoding="utf-8")

    return repo


class TestHarnessGenerator:
    """Test suite for autonomous harness synthesizer."""

    def test_sanitize_and_format_name(self):
        assert _sanitize_name("My Custom-App 2.0") == "my_custom_app_2_0"
        assert _sanitize_name("123editor") == "app_123editor"
        assert _format_display_name("shotcut_studio") == "Shotcut Studio"

    def test_codebase_analysis(self, mock_software_repo: Path):
        synthesizer = HarnessSynthesizer(work_dir=mock_software_repo.parent / "extra_work")
        analysis = synthesizer.analyze_codebase(mock_software_repo, "mock_editor")

        assert analysis.software_name == "mock_editor"
        assert analysis.total_files >= 5
        assert "Python" in analysis.languages
        assert "C++" in analysis.languages
        assert "JSON" in analysis.data_formats
        assert "XML" in analysis.data_formats
        assert any("main.py" in ep for ep in analysis.entrypoints)
        assert len(analysis.domain_keywords) > 0

    def test_architecture_design(self, mock_software_repo: Path):
        synthesizer = HarnessSynthesizer(work_dir=mock_software_repo.parent / "extra_work")
        analysis = synthesizer.analyze_codebase(mock_software_repo, "mock_editor")
        design = synthesizer.design_architecture(analysis)

        assert design.software_name == "mock_editor"
        group_names = [g.name for g in design.command_groups]
        assert "project" in group_names
        assert "session" in group_names
        assert "export" in group_names
        assert len(design.sop_markdown) > 50

    def test_scaffolding_generation(self, mock_software_repo: Path):
        synthesizer = HarnessSynthesizer(work_dir=mock_software_repo.parent / "extra_work")
        analysis = synthesizer.analyze_codebase(mock_software_repo, "mock_editor")
        design = synthesizer.design_architecture(analysis)
        
        output_dir = mock_software_repo.parent / "output"
        created = synthesizer.scaffold_package(design, output_parent_dir=output_dir)

        assert "setup_py" in created
        assert "cli_py" in created
        assert "session_py" in created
        assert "project_py" in created
        assert "test_core_py" in created

        cli_content = created["cli_py"].read_text(encoding="utf-8")
        assert "click.group" in cli_content
        assert "--json" in cli_content
        assert "SessionManager" in cli_content

    def test_ast_skill_markdown_generation(self, mock_software_repo: Path):
        synthesizer = HarnessSynthesizer(work_dir=mock_software_repo.parent / "extra_work")
        analysis = synthesizer.analyze_codebase(mock_software_repo, "mock_editor")
        design = synthesizer.design_architecture(analysis)
        output_dir = mock_software_repo.parent / "output"
        created = synthesizer.scaffold_package(design, output_parent_dir=output_dir)

        skill_md = synthesizer.generate_skill_markdown(
            cli_file_path=created["cli_py"],
            software_name="mock_editor"
        )

        assert "---" in skill_md
        assert "name: extra-mock_editor" in skill_md
        assert "Dual-Plane Architecture" in skill_md
        assert "extra_harness_run" in skill_md
        assert "| Group | Command | Description |" in skill_md

    def test_end_to_end_synthesis_and_test_execution(self, mock_software_repo: Path):
        synthesizer = HarnessSynthesizer(work_dir=mock_software_repo.parent / "extra_work")
        result = synthesizer.synthesize(
            software_path_or_repo=str(mock_software_repo),
            phase_target="all"
        )

        assert result["status"] == "success"
        assert result["software"] == "mock_editor"
        assert "files" in result
        assert "skill_path" in result
        
        # Verify the generated unit tests executed and passed
        test_res = result.get("test_results", {})
        if test_res.get("status") != "skipped":
            assert test_res.get("passed") is True
