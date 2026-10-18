"""
Project Extra — Test Suite for Universal CLI Harness Runner & CLI-Hub Integration
Tests execution, JSON extraction, artifact detection, registry resolution, and MCP tool handlers.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from extra.fastpath.cli_harness import (
    HarnessResult,
    UniversalHarnessRunner,
    _extract_json_payload,
    execute_harness,
    is_harness_available,
    resolve_harness,
)
from extra.fastpath.cli_hub import (
    CliHubManager,
    get_cli_hub,
)
from extra.fastpath.bridge import execute_bridge, _registry
from extra.fastpath.visualizer import DualPlaneVisualizer, visualize_harness_outcome
from extra.mcp.server import extra_harness_run, extra_hub_manage


class TestHarnessExtractionAndNormalization:
    """Tests name normalization and resilient JSON payload extraction."""

    def test_normalize_harness_name(self):
        assert UniversalHarnessRunner.normalize_harness_name("blender") == "blender"
        assert UniversalHarnessRunner.normalize_harness_name("cli-anything-blender") == "blender"
        assert UniversalHarnessRunner.normalize_harness_name("cli_anything-gimp") == "gimp"
        assert UniversalHarnessRunner.normalize_harness_name("CLI_ANYTHING_FREECAD") == "freecad"
        assert UniversalHarnessRunner.normalize_harness_name("cli-anything-slay-the-spire-ii") == "slay-the-spire-ii"

    def test_extract_pure_json(self):
        sample = '{"status": "success", "mesh_id": 42}'
        payload = _extract_json_payload(sample)
        assert payload == {"status": "success", "mesh_id": 42}

    def test_extract_json_with_banner_and_logs(self):
        sample = """
        ========================================
        * Welcome to CLI-Anything GIMP REPL *
        ========================================
        [INFO] Initializing headless image engine...
        {"project": "banner.xcf", "layers": 3, "exported": true}
        [INFO] Shutdown complete.
        """
        payload = _extract_json_payload(sample)
        assert payload == {"project": "banner.xcf", "layers": 3, "exported": True}

    def test_extract_invalid_json(self):
        assert _extract_json_payload("Fatal error: memory fault") is None
        assert _extract_json_payload("") is None


class TestHarnessResolver:
    """Tests resolution of CLI binaries, python modules, and workspace scripts."""

    def test_resolve_via_which(self):
        runner = UniversalHarnessRunner()
        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: "/usr/bin/cli-anything-gimp" if "gimp" in cmd else None
            res = runner.resolve_harness("gimp")
            assert res == ["/usr/bin/cli-anything-gimp"]

    def test_resolve_via_python_module(self):
        runner = UniversalHarnessRunner()
        with patch("shutil.which", return_value=None):
            with patch("importlib.util.find_spec") as mock_find:
                mock_find.return_value = MagicMock()
                res = runner.resolve_harness("freecad")
                assert res == [sys.executable, "-m", "cli_anything.freecad.freecad_cli"]

    def test_resolve_not_found(self):
        runner = UniversalHarnessRunner()
        with patch("shutil.which", return_value=None):
            with patch("importlib.util.find_spec", return_value=None):
                with patch.object(runner, "workspace_root", Path("/nonexistent"), create=True):
                    res = runner.resolve_harness("nonexistent_app_xyz")
                    assert res is None


class TestHarnessExecution:
    """Tests subprocess execution, artifact detection, and error handling."""

    def test_execute_success_with_json(self, tmp_path):
        runner = UniversalHarnessRunner(workspace_dir=tmp_path)

        def fake_subprocess_run(cmd, cwd, capture_output, text, timeout, env):
            # Simulate CLI creating an artifact file and printing JSON
            out_file = Path(cwd) / "render.png"
            out_file.write_text("fake png bytes")
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout=json.dumps({"success": True, "output": str(out_file)}),
                stderr="",
            )

        with patch.object(runner, "resolve_harness", return_value=["fake-cli"]):
            with patch("subprocess.run", side_effect=fake_subprocess_run):
                result = runner.execute("blender", ["render", "--samples", "64"])

                assert result.success is True
                assert result.returncode == 0
                assert result.data == {"success": True, "output": str(tmp_path / "render.png")}
                assert len(result.artifacts_created) == 1
                assert "render.png" in result.artifacts_created[0]
                assert result.latency_ms > 0

    def test_execute_missing_harness_error(self):
        runner = UniversalHarnessRunner()
        with patch.object(runner, "resolve_harness", return_value=None):
            result = runner.execute("unknown-app", ["do-something"])
            assert result.success is False
            assert result.returncode == -1
            assert "not found on system PATH" in result.error
            assert "extra_hub_manage" in result.error

    def test_execute_subprocess_timeout(self, tmp_path):
        runner = UniversalHarnessRunner(workspace_dir=tmp_path)
        with patch.object(runner, "resolve_harness", return_value=["mock-cli"]):
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["mock-cli"], timeout=5)):
                result = runner.execute("gimp", ["heavy-filter"], timeout_sec=5)
                assert result.success is False
                assert result.returncode == -2
                assert "timed out after 5s" in result.error


class TestCliHubManager:
    """Tests registry parsing, searching, and package management."""

    @pytest.fixture
    def mock_registry(self, tmp_path):
        reg_data = {
            "clis": [
                {
                    "name": "blender",
                    "display_name": "Blender 3D",
                    "version": "1.0.0",
                    "category": "3d",
                    "description": "Agent-native 3D modeling and rendering CLI",
                    "install_cmd": "pip install git+https://github.com/HKUDS/CLI-Anything.git#subdirectory=blender/agent-harness",
                },
                {
                    "name": "gimp",
                    "display_name": "GIMP",
                    "version": "0.9.5",
                    "category": "image",
                    "description": "Image manipulation and layer management",
                    "install_cmd": "pip install git+https://github.com/HKUDS/CLI-Anything.git#subdirectory=gimp/agent-harness",
                },
                {
                    "name": "libreoffice",
                    "display_name": "LibreOffice",
                    "version": "1.1.0",
                    "category": "office",
                    "description": "Headless document conversion and spreadsheets",
                    "install_cmd": "pip install git+https://github.com/HKUDS/CLI-Anything.git#subdirectory=libreoffice/agent-harness",
                },
            ]
        }
        reg_file = tmp_path / "registry.json"
        reg_file.write_text(json.dumps(reg_data), encoding="utf-8")
        pub_file = tmp_path / "public_registry.json"
        pub_file.write_text(json.dumps({"clis": []}), encoding="utf-8")
        return tmp_path

    def test_list_and_search_harnesses(self, mock_registry):
        hub = CliHubManager(workspace_root=mock_registry)
        all_items = hub.list_harnesses()
        assert len(all_items) == 3

        image_items = hub.list_harnesses(category="image")
        assert len(image_items) == 1
        assert image_items[0]["name"] == "gimp"

        searched = hub.search_harnesses("3D")
        assert len(searched) == 1
        assert searched[0]["name"] == "blender"

    def test_get_harness_info(self, mock_registry):
        hub = CliHubManager(workspace_root=mock_registry)
        info = hub.get_harness_info("libreoffice")
        assert info is not None
        assert info["display_name"] == "LibreOffice"
        assert info["category"] == "office"

        assert hub.get_harness_info("nonexistent") is None

    def test_install_harness_already_installed(self, mock_registry):
        hub = CliHubManager(workspace_root=mock_registry)
        with patch("extra.fastpath.cli_harness.is_harness_available", return_value=True):
            res = hub.install_harness("blender")
            assert res["success"] is True
            assert res["already_installed"] is True


class TestBridgeIntegration:
    """Tests the UniversalBridgeRegistry 'harness' runtime integration."""

    def test_bridge_runtime_registered(self):
        runtimes = _registry.list_runtimes()
        assert "harness" in runtimes

    def test_execute_bridge_with_harness(self):
        mock_result = HarnessResult(
            harness="blender",
            success=True,
            returncode=0,
            stdout='{"cube_created": true}',
            stderr="",
            data={"cube_created": True},
            artifacts_created=["model.blend"],
            latency_ms=12.5,
        )
        with patch("extra.fastpath.cli_harness.execute_harness", return_value=mock_result):
            bridge_res = execute_bridge(
                runtime="harness",
                payload="blender",
                args=["mesh", "add-cube"],
            )
            assert bridge_res.runtime == "harness"
            assert bridge_res.success is True
            assert bridge_res.returncode == 0
            assert bridge_res.artifacts_created == ["model.blend"]
            assert bridge_res.metadata.get("data") == {"cube_created": True}


class TestServerMCPTools:
    """Tests extra_harness_run and extra_hub_manage MCP tools."""

    def test_extra_harness_run_tool(self):
        mock_res = HarnessResult(
            harness="gimp",
            success=True,
            returncode=0,
            stdout="{}",
            stderr="",
            data={"filter_applied": True},
        )
        with patch("extra.mcp.server.execute_harness", return_value=mock_res):
            out = extra_harness_run(harness="gimp", command=["filter", "blur"])
            assert out["success"] is True
            assert out["harness"] == "gimp"
            assert out["data"] == {"filter_applied": True}

    def test_extra_hub_manage_tool_actions(self):
        mock_hub = MagicMock()
        mock_hub.list_harnesses.return_value = [{"name": "blender"}]
        mock_hub.search_harnesses.return_value = [{"name": "freecad"}]
        mock_hub.get_harness_info.return_value = {"name": "inkscape"}
        mock_hub.is_harness_installed.return_value = True
        mock_hub.install_harness.return_value = {"success": True, "name": "krita"}

        with patch("extra.mcp.server.get_cli_hub", return_value=mock_hub):
            # Test list
            out_list = extra_hub_manage(action="list")
            assert out_list["success"] is True
            assert len(out_list["clis"]) == 1

            # Test search
            out_search = extra_hub_manage(action="search", query="cad")
            assert out_search["success"] is True
            assert len(out_search["results"]) == 1

            # Test info
            out_info = extra_hub_manage(action="info", harness_name="inkscape")
            assert out_info["success"] is True
            assert out_info["info"]["name"] == "inkscape"

            # Test status
            out_status = extra_hub_manage(action="status", harness_name="blender")
            assert out_status["success"] is True
            assert out_status["is_installed"] is True

            # Test install
            out_install = extra_hub_manage(action="install", harness_name="krita")
            assert out_install["success"] is True


class TestDualPlaneVisualizer:
    """Tests Dual-Plane 'Glass & Engine' visualizer coordination."""

    def test_find_target_artifact_from_artifacts_created(self, tmp_path):
        blend_file = tmp_path / "scene.blend"
        blend_file.write_text("dummy blend data")
        log_file = tmp_path / "build.log"
        log_file.write_text("build log")

        found = DualPlaneVisualizer.find_target_artifact(
            artifacts_created=[str(log_file), str(blend_file)],
        )
        assert found is not None
        assert found.name == "scene.blend"

    def test_find_target_artifact_from_json_data(self, tmp_path):
        fcstd_file = tmp_path / "bracket.fcstd"
        fcstd_file.write_text("dummy fcstd data")

        found = DualPlaneVisualizer.find_target_artifact(
            artifacts_created=[],
            data={"success": True, "output_path": str(fcstd_file)},
        )
        assert found is not None
        assert found.name == "bracket.fcstd"

    def test_find_target_artifact_from_cli_args(self, tmp_path):
        png_file = tmp_path / "poster.png"
        png_file.write_text("dummy png data")

        found = DualPlaneVisualizer.find_target_artifact(
            artifacts_created=[],
            args=["export", "--output", str(png_file)],
        )
        assert found is not None
        assert found.name == "poster.png"

    def test_visualize_with_launch_app(self, tmp_path):
        blend_file = tmp_path / "model.blend"
        blend_file.write_text("dummy")

        vis = DualPlaneVisualizer()
        mock_launch_res = MagicMock()
        mock_launch_res.matched_hwnd = 1001
        mock_launch_res.matched_title = "Blender [model.blend]"
        mock_launch_res.target_executed = "blender.exe"

        with patch("extra.fastpath.visualizer.resolve_executable", return_value="C:\\Program Files\\Blender\\blender.exe"):
            with patch("extra.fastpath.visualizer.launch_app", return_value=mock_launch_res) as mock_launch:
                with patch("extra.fastpath.visualizer.force_activate_window") as mock_activate:
                    with patch("extra.core.indicators.get_indicator_controller") as mock_ctrl:
                        with patch("extra.core.soul.gateman._default_gateman.wait_until_settled", return_value={"settled": True, "duration_ms": 25.0}):
                            res = vis.visualize(
                                harness="blender",
                                artifacts_created=[str(blend_file)],
                                wait_for_settle=True,
                                play_chime=True,
                            )
                            assert res["visualized"] is True
                            assert res["method"] == "launch_app"
                            assert res["window_hwnd"] == 1001
                            assert res["window_title"] == "Blender [model.blend]"
                            assert res["settle_ms"] == 25.0
                            mock_launch.assert_called_once()
                            mock_activate.assert_called_once_with(1001)

    def test_visualize_fallback_to_open_uri(self, tmp_path):
        pdf_file = tmp_path / "doc.pdf"
        pdf_file.write_text("dummy pdf")

        vis = DualPlaneVisualizer()
        with patch("extra.fastpath.visualizer.resolve_executable", return_value=None):
            with patch("extra.fastpath.visualizer.open_uri", return_value=True) as mock_open:
                res = vis.visualize(
                    harness="libreoffice",
                    artifacts_created=[str(pdf_file)],
                    wait_for_settle=False,
                    play_chime=False,
                )
                assert res["visualized"] is True
                assert res["method"] == "open_uri"
                mock_open.assert_called_once_with(str(pdf_file.resolve()))

    def test_auto_visualize_in_harness_runner(self, tmp_path):
        runner = UniversalHarnessRunner(workspace_dir=tmp_path)
        out_file = tmp_path / "render.png"

        def fake_subprocess_run(cmd, cwd, capture_output, text, timeout, env):
            out_file.write_text("fake png")
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout=json.dumps({"success": True, "output": str(out_file)}),
                stderr="",
            )

        with patch.object(runner, "resolve_harness", return_value=["mock-cli"]):
            with patch("subprocess.run", side_effect=fake_subprocess_run):
                with patch("extra.fastpath.visualizer.visualize_harness_outcome", return_value={"visualized": True, "window_title": "Photo Viewer"}):
                    res = runner.execute("gimp", ["export", "-o", str(out_file)], auto_visualize=True)
                    assert res.success is True
                    assert "visualization" in res.metadata
                    assert res.metadata["visualization"]["visualized"] is True
                    assert res.metadata["visualization"]["window_title"] == "Photo Viewer"

