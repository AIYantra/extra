"""
Tests for Project Extra — Ground-Truth State Critic
Guarantees independent validation of UI runtime state and prevents epistemic drift.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from extra.core.soul.state_critic import (
    GroundTruthStateCritic,
    StateAuditClaim,
    StateAuditResult,
    audit_ground_truth_state,
)


def test_state_critic_detects_sheet_tab_deficit():
    # Simulate actual Google Sheets state from the benchmark run: only 3 tabs created
    html = """
    <html>
      <body>
        <div role="tablist">
          <div role="tab" class="docs-sheet-tab"><span>Executive Summary</span></div>
          <div role="tab" class="docs-sheet-tab"><span>Financial Model</span></div>
          <div role="tab" class="docs-sheet-tab"><span>Marketing Strategy</span></div>
        </div>
      </body>
    </html>
    """

    claims = {
        "doc_type": "spreadsheet",
        "expected_tabs": 9,
    }

    result = audit_ground_truth_state(claims, page_html=html)

    assert result.passed is False
    assert result.ground_truth["tab_count"] == 3
    assert len(result.defects) == 1
    assert "Tab count deficit: Expected 9 tabs, but found only 3" in result.defects[0]
    assert len(result.audit_hash) == 64
    assert "DEFECTS DETECTED" in result.report_text


def test_state_critic_passes_when_all_tabs_present():
    tabs_html = "".join([f'<div role="tab" class="tab">Tab {i}</div>' for i in range(1, 10)])
    html = f"<html><body><div role='tablist'>{tabs_html}</div></body></html>"

    claims = {"expected_tabs": 9}
    result = audit_ground_truth_state(claims, page_html=html)

    assert result.passed is True
    assert result.score == 1.0
    assert result.ground_truth["tab_count"] == 9
    assert len(result.defects) == 0
    assert "ALL VERIFICATION CHECKS SATISFIED" in result.report_text


def test_state_critic_detects_slide_deficit():
    # Only 1 slide present
    html = """
    <html>
      <body>
        <div class="filmstrip">
          <div role="option" class="filmstrip-slide">Slide 1</div>
        </div>
      </body>
    </html>
    """

    claims = {"expected_slides": 8}
    result = audit_ground_truth_state(claims, page_html=html)

    assert result.passed is False
    assert result.ground_truth["slide_count"] == 1
    assert any("Slide count deficit: Expected 8 slides, but found only 1" in d for d in result.defects)


def test_state_critic_detects_empty_document():
    # Empty Google Docs body (0 words)
    html = """
    <html>
      <body>
        <div class="kix-appview document-editor">
          <!-- Empty document body -->
        </div>
      </body>
    </html>
    """

    claims = {"min_words": 150, "expected_sections": 5}
    result = audit_ground_truth_state(claims, page_html=html)

    assert result.passed is False
    assert result.ground_truth["word_count"] == 0
    assert any("Document text deficit" in d for d in result.defects)
    assert any("Section count deficit" in d for d in result.defects)


def test_state_critic_accessibility_probe():
    critic = GroundTruthStateCritic()

    mock_el1 = MagicMock()
    mock_el1.control_type = "TabItem"
    mock_el1.name = "Sheet1"

    mock_el2 = MagicMock()
    mock_el2.control_type = "TabItem"
    mock_el2.name = "Sheet2"

    mock_plane = MagicMock()
    mock_plane.inspect_tree.return_value = [mock_el1, mock_el2]

    with patch("extra.core.soul.state_critic.get_accessibility_plane", return_value=mock_plane):
        claim = StateAuditClaim(expected_tabs=5)
        result = critic.audit_state(claim, window_title="Google Sheets")

    assert result.passed is False
    assert result.ground_truth["tab_count"] == 2
    assert any("Tab count deficit: Expected 5 tabs, but found only 2" in d for d in result.defects)


def test_accessibility_plane_has_inspect_tree():
    """Verify that UIAutomationPlane has inspect_tree method implemented."""
    from extra.core.platform.windows.uia_plane import UIAutomationPlane
    assert hasattr(UIAutomationPlane, "inspect_tree")
    assert callable(getattr(UIAutomationPlane, "inspect_tree"))


def test_state_critic_probe_error_fails_audit():
    """Verify that an exception in accessibility probe causes audit to fail rather than silently pass."""
    critic = GroundTruthStateCritic()
    mock_plane = MagicMock()
    mock_plane.inspect_tree.side_effect = RuntimeError("COM channel disrupted")

    with patch("extra.core.soul.state_critic.get_accessibility_plane", return_value=mock_plane):
        claim = StateAuditClaim()
        result = critic.audit_state(claim, window_title="Settings")

    assert result.passed is False
    assert "probe_error" in result.ground_truth
    assert any("Accessibility sensor probe failed" in d for d in result.defects)
