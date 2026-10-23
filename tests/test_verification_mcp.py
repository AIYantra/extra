"""
Tests for Project Extra — Anti-Shortcut Verification MCP Tools
Validates extra_verify_state, extra_verify_lineage, extra_workspace_export,
and extra_task_complete ground-truth guardrail.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from extra.mcp.server import (
    extra_task_complete,
    extra_verify_lineage,
    extra_verify_state,
    extra_workspace_export,
)


def test_extra_verify_lineage_mcp(tmp_path: Path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4\n/Producer (Google Docs)\n%%EOF")

    res = extra_verify_lineage(str(pdf), expected_origin="official_web_export")
    assert res["valid"] is True
    assert res["detected_origin"] == "official_web_export"
    assert res["producer"] == "Google Docs"


def test_extra_verify_lineage_mcp_rejects_substitutions(tmp_path: Path):
    pdf = tmp_path / "fake.pdf"
    pdf.write_bytes(b"%PDF-1.4\n/Producer (Skia/PDF m128)\n%%EOF")

    res = extra_verify_lineage(str(pdf), expected_origin="official_web_export")
    assert res["valid"] is False
    assert res["detected_origin"] == "programmatic_local"
    assert any("local browser print" in d for d in res["defects"])


def test_extra_verify_state_mcp():
    with patch("extra.core.soul.state_critic.get_accessibility_plane") as mock_plane_func:
        mock_plane = MagicMock()
        t1, t2, t3 = MagicMock(), MagicMock(), MagicMock()
        t1.control_type, t1.name = "TabItem", "Sheet 1"
        t2.control_type, t2.name = "TabItem", "Sheet 2"
        t3.control_type, t3.name = "TabItem", "Sheet 3"
        mock_plane.inspect_tree.return_value = [t1, t2, t3]
        mock_plane_func.return_value = mock_plane

        # Expected 5 tabs, only 3 exist
        res = extra_verify_state(expected_tabs=5)
        assert res["success"] is True
        assert res["passed"] is False
        assert res["ground_truth"]["tab_count"] == 3
        assert any("Tab count deficit: Expected 5 tabs, but found only 3" in d for d in res["defects"])


def test_extra_task_complete_rejects_hallucinated_claims():
    with patch("extra.core.soul.state_critic.get_accessibility_plane") as mock_plane_func:
        mock_plane = MagicMock()
        mock_plane.inspect_tree.return_value = []  # 0 tabs found
        mock_plane_func.return_value = mock_plane

        # Agent claims 9 tabs created successfully
        claims = {"expected_tabs": 9}
        res = extra_task_complete(summary="Completed 9 tabs", success=True, claims=claims, auto_screenshot=False, play_chime=False)

        assert res["success"] is False
        assert res["status"] == "claims_deficit"
        assert "TASK COMPLETION REJECTED" in res["error"]
        assert len(res["audit_hash"]) == 64
        assert res["ground_truth"]["tab_count"] == 0


def test_extra_workspace_export_mcp(tmp_path: Path):
    target = tmp_path / "exported.pdf"
    with patch("extra.fastpath.web_workspace.trigger_workspace_export") as mock_export:
        mock_export.return_value = {
            "success": True,
            "file_path": str(target),
            "file_size": 1024,
            "source": "official_workspace_export",
        }
        res = extra_workspace_export(
            url_or_id="https://docs.google.com/document/d/doc123/edit",
            output_path=str(target),
            export_format="pdf",
        )

        assert res["success"] is True
        assert res["file_path"] == str(target)
        assert res["source"] == "official_workspace_export"


def test_extra_workspace_export_local_dir_mcp(tmp_path: Path):
    """Verify extra_workspace_export packages local workspace directory into zip."""
    ws = tmp_path / "my_project"
    ws.mkdir()
    (ws / "file1.txt").write_text("Hello World", encoding="utf-8")
    (ws / "sub").mkdir()
    (ws / "sub" / "file2.json").write_text('{"a": 1}', encoding="utf-8")

    res = extra_workspace_export(
        workspace_dir=str(ws),
        archive_name="project.zip",
    )

    assert res["success"] is True
    assert res["export_format"] == "zip"
    assert "project.zip" in res["output_path"]
    assert Path(res["output_path"]).exists()
    assert res["size_bytes"] > 0


def test_extra_verify_lineage_workspace_path_mcp(tmp_path: Path):
    """Verify extra_verify_lineage verifies workspace directory and manifests."""
    ws = tmp_path / "verified_workspace"
    exports = ws / "exports"
    exports.mkdir(parents=True)
    manifest = exports / "lineage_manifest.json"
    manifest.write_text('{"manifest": true}', encoding="utf-8")

    from extra.mcp.server import extra_verify_lineage
    res = extra_verify_lineage(workspace_path=str(ws))

    assert res["valid"] is True
    assert res["detected_origin"] == "manifest_verified"
    assert str(manifest) in res["file_path"]


def test_tripartite_actuator_telemetry_contract():
    """Verify that all actuator tools return decoupled action_dispatched, action_executed, and verification_status."""
    from extra.mcp.server import extra_click, extra_type, extra_hotkey, extra_drag, extra_batch_actions
    from PIL import Image
    from extra.core.platform.base import CaptureResult

    dummy_img = Image.new("RGB", (200, 200), "white")
    cap = CaptureResult(image=dummy_img, width=200, height=200, monitor_index=0, duration_ms=1.0)

    # 1. extra_type
    with patch("extra.mcp.server.instant_type"):
        res_type = extra_type(text="status update", press_enter=True)
        assert res_type["success"] is True
        assert res_type["action_dispatched"] is True
        assert res_type["action_executed"] is True
        assert res_type["verification_status"] == "unconfirmed"

    # 2. extra_hotkey
    with patch("extra.mcp.server.send_hotkey"):
        res_hotkey = extra_hotkey(keys=["enter"])
        assert res_hotkey["success"] is True
        assert res_hotkey["action_dispatched"] is True
        assert res_hotkey["action_executed"] is True
        assert res_hotkey["verification_status"] == "unconfirmed"

        res_hotkey_copy = extra_hotkey(keys=["ctrl", "c"])
        assert res_hotkey_copy["verification_status"] == "skipped"

    # 3. extra_drag
    with patch("extra.mcp.server.mouse_drag"):
        res_drag = extra_drag(start_x=10, start_y=10, end_x=100, end_y=100)
        assert res_drag["success"] is True
        assert res_drag["action_dispatched"] is True
        assert res_drag["action_executed"] is True
        assert res_drag["verification_status"] == "unconfirmed"

    # 4. extra_click
    with patch("extra.mcp.server.capture_screen", return_value=cap), patch("extra.mcp.server.mouse_click"):
        res_click = extra_click(x=50, y=50)
        assert res_click["action_dispatched"] is True
        assert res_click["action_executed"] is True
        assert "verification_status" in res_click

    # 5. extra_batch_actions
    with patch("extra.mcp.server.execute_batch_actions", return_value={"total_duration_ms": 10.0}):
        res_batch = extra_batch_actions(actions=[{"action": "sleep", "ms": 10}])
        assert res_batch["action_dispatched"] is True
        assert res_batch["action_executed"] is True
        assert "verification_status" in res_batch



def test_duplicate_action_guard_mcp_enforcement():
    """Validates that MCP actuator tools reject duplicate unconfirmed actions unless force=True."""
    from extra.mcp.server import _stall_breaker, extra_type, extra_hotkey, extra_task_complete
    from unittest.mock import patch

    _stall_breaker.clear_consequential_history()

    # 1. First type with press_enter succeeds
    with patch("extra.mcp.server.instant_type"):
        res1 = extra_type(text="Send confidential wire", press_enter=True)
        assert res1["success"] is True
        assert res1["action_dispatched"] is True
        assert res1["verification_status"] == "unconfirmed"

        # 2. Immediate repeat of identical text with press_enter is blocked by guard
        res2 = extra_type(text="Send confidential wire", press_enter=True)
        assert res2["success"] is False
        assert res2["action_dispatched"] is False
        assert res2["action_executed"] is False
        assert res2["verification_status"] == "blocked"
        assert res2["guard_triggered"] == "duplicate_action_guard"
        assert "Duplicate Action Guard" in res2["error"]

        # 3. With force=True, duplicate is allowed to proceed
        res3 = extra_type(text="Send confidential wire", press_enter=True, force=True)
        assert res3["success"] is True
        assert res3["action_dispatched"] is True

    # 4. extra_task_complete clears history
    with patch("extra.mcp.server.get_indicator_controller"):
        extra_task_complete(summary="Done", auto_screenshot=False, play_chime=False)
        assert len(_stall_breaker._consequential_history) == 0
