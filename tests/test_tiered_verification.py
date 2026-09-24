"""
Project Extra — Tests for Tiered Verification Engine (Phase 1)
Validates Tier 1 in-memory perceptual settle detection and inline auto_settle
integration within compound hardware batch dispatch.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from extra.core.soul.gateman import SoulGateman, wait_until_settled
from extra.core.input_engine import execute_batch_actions
from extra.mcp.server import extra_batch_actions


class TestTieredVerificationPhase1:
    """Test suite for Tier 1 zero-latency perceptual settle detection and batch dispatch."""

    def test_soul_gateman_settle_parameters(self) -> None:
        """Verifies fine-grained settle parameter propagation in SoulGateman."""
        gateman = SoulGateman()
        
        # Test with synthetic stable frames
        stable_img = Image.new("RGB", (64, 64), color=(100, 100, 100))
        mock_cap = MagicMock()
        mock_cap.image = stable_img

        with patch("extra.core.soul.gateman.capture_screen", return_value=mock_cap):
            res = gateman.wait_until_settled(
                timeout_sec=0.3,
                settle_frames=2,
                check_interval_ms=10,
                hash_diff_threshold=1,
            )
            assert res["settled"] is True
            assert res["frames_inspected"] >= 2
            assert res["duration_ms"] < 250.0

    def test_module_wait_until_settled_forwards_parameters(self) -> None:
        """Verifies module-level wait_until_settled forwards fine-grained params."""
        stable_img = Image.new("RGB", (64, 64), color=(200, 50, 50))
        mock_cap = MagicMock()
        mock_cap.image = stable_img

        with patch("extra.core.soul.gateman.capture_screen", return_value=mock_cap):
            res = wait_until_settled(
                timeout_sec=0.2,
                settle_frames=2,
                check_interval_ms=10,
                hash_diff_threshold=1,
            )
            assert res["settled"] is True
            assert "duration_ms" in res

    def test_execute_batch_actions_with_auto_settle_true(self) -> None:
        """Verifies that auto_settle=True invokes SoulGateman settle for physical actions."""
        actions: List[Dict[str, Any]] = [
            {"action": "hotkey", "keys": ["ctrl", "c"]},
            {"action": "click", "x": 100, "y": 100},
        ]

        mock_settle = {
            "settled": True,
            "duration_ms": 12.5,
            "frames_inspected": 2,
            "final_hash": "abcd1234",
        }

        with patch("extra.core.platform.windows.input_engine.send_hotkey"), \
             patch("extra.core.platform.windows.input_engine.mouse_click"), \
             patch("extra.core.soul.gateman.wait_until_settled", return_value=mock_settle) as mock_wait:

            res = execute_batch_actions(actions, auto_settle=True)
            assert res["success"] is True
            assert res["executed_count"] == 2

            # Physical actions should have settled and settle_ms populated
            for item in res["actions"]:
                assert item.get("settled") is True
                assert item.get("settle_ms") == 12.5

            assert mock_wait.call_count >= 2

    def test_execute_batch_actions_with_auto_settle_false(self) -> None:
        """Verifies that auto_settle=False bypasses SoulGateman settle checks."""
        actions: List[Dict[str, Any]] = [
            {"action": "hotkey", "keys": ["esc"]},
            {"action": "click", "x": 50, "y": 50},
        ]

        with patch("extra.core.platform.windows.input_engine.send_hotkey"), \
             patch("extra.core.platform.windows.input_engine.mouse_click"), \
             patch("extra.core.soul.gateman.wait_until_settled") as mock_wait, \
             patch("time.sleep") as mock_sleep:

            res = execute_batch_actions(actions, auto_settle=False)
            assert res["success"] is True
            assert res["executed_count"] == 2

            # SoulGateman should NOT have been called
            mock_wait.assert_not_called()
            # Standard physical settle sleep should be invoked
            assert mock_sleep.call_count >= 2

    def test_execute_batch_actions_custom_settle_ms(self) -> None:
        """Verifies that explicit settle_ms in an action overrides auto_settle."""
        actions: List[Dict[str, Any]] = [
            {"action": "click", "x": 200, "y": 200, "settle_ms": 80},
        ]

        with patch("extra.core.platform.windows.input_engine.mouse_click"), \
             patch("extra.core.soul.gateman.wait_until_settled") as mock_wait, \
             patch("time.sleep") as mock_sleep:

            res = execute_batch_actions(actions, auto_settle=True)
            assert res["success"] is True
            mock_wait.assert_not_called()
            mock_sleep.assert_called_with(0.08)

    def test_mcp_extra_batch_actions_auto_settle_integration(self) -> None:
        """Verifies that MCP tool extra_batch_actions accepts and forwards auto_settle."""
        actions: List[Dict[str, Any]] = [
            {"action": "sleep", "ms": 10},
        ]

        res = extra_batch_actions(actions=actions, auto_settle=True)
        assert res["success"] is True
        assert res["executed_count"] == 1

    def test_batch_typing_throttle_performance(self) -> None:
        """Verifies fast-path typing executes without per-character settle stalls."""
        actions: List[Dict[str, Any]] = [
            {"action": "type", "text": "245.12/383.29=", "press_enter": True},
        ]

        with patch("extra.core.platform.windows.input_engine.instant_type"), \
             patch("extra.core.soul.gateman.wait_until_settled") as mock_wait:

            res = execute_batch_actions(actions, auto_settle=True)
            assert res["success"] is True
            # Typing should NOT trigger Gateman settle between characters
            mock_wait.assert_not_called()


class TestTieredVerificationPhase2:
    """Test suite for Tier 2 closed-loop focus verification, stroke ink telemetry, and web settle hooks."""

    def test_focus_closed_loop_verification_success(self) -> None:
        """Verifies focus action validates foreground window and returns verified_focus=True."""
        actions: List[Dict[str, Any]] = [
            {"action": "focus", "window_title": "Notepad"},
        ]

        mock_win = MagicMock()
        mock_win.hwnd = 12345
        mock_win.title = "Untitled - Notepad"

        mock_fg = MagicMock()
        mock_fg.hwnd = 12345
        mock_fg.title = "Untitled - Notepad"

        with patch("extra.core.focus.find_window_by_title", return_value=mock_win), \
             patch("extra.core.focus.force_activate_window", return_value=True), \
             patch("extra.core.focus.get_foreground_window", return_value=mock_fg):

            res = execute_batch_actions(actions, auto_settle=False)
            assert res["success"] is True
            item = res["actions"][0]
            assert item["action"] == "focus"
            assert item["verified_focus"] is True
            assert item["active_hwnd"] == 12345
            assert "Notepad" in item["active_title"]

    def test_focus_closed_loop_verification_failure(self) -> None:
        """Verifies focus action returns verified_focus=False when window switch fails."""
        actions: List[Dict[str, Any]] = [
            {"action": "focus", "window_title": "Blender"},
        ]

        mock_win = MagicMock()
        mock_win.hwnd = 99999
        mock_win.title = "Blender"

        mock_fg = MagicMock()
        mock_fg.hwnd = 11111
        mock_fg.title = "Chrome"

        with patch("extra.core.focus.find_window_by_title", return_value=mock_win), \
             patch("extra.core.focus.force_activate_window", return_value=False), \
             patch("extra.core.focus.get_foreground_window", return_value=mock_fg):

            res = execute_batch_actions(actions, auto_settle=False)
            item = res["actions"][0]
            assert item["action"] == "focus"
            assert item["verified_focus"] is False
            assert item["success"] is False
            assert item["active_hwnd"] == 11111

    def test_batch_actions_strict_ink_enforcement(self) -> None:
        """Verifies strict_ink=True fails batch if no ink deposited along stroke trajectory."""
        actions: List[Dict[str, Any]] = [
            {"action": "click", "x": 100, "y": 100},
            {"action": "stroke", "points": [[100, 100], [150, 150]]},
        ]

        # Mock capture_screen to simulate zero pixel change (ghost stroke)
        blank_img = Image.new("RGB", (200, 200), (255, 255, 255))
        mock_cap = MagicMock()
        mock_cap.image = blank_img

        with patch("extra.mcp.server.capture_screen", return_value=mock_cap), \
             patch("extra.core.platform.windows.input_engine.mouse_click"), \
             patch("extra.core.platform.windows.input_engine.mouse_stroke"):

            res = extra_batch_actions(actions=actions, auto_settle=False, strict_ink=True)
            assert res["success"] is False
            assert "GHOST STROKES" in res.get("error", "")

    def test_browser_wait_for_settle_hook(self) -> None:
        """Verifies browser wait_for_settle hook returns fast DOM and network settle telemetry."""
        from extra.fastpath.browser import BrowserFastPath, execute_browser_action

        browser = BrowserFastPath(headless=True)
        mock_page = MagicMock()
        mock_page.url = "https://example.com"
        mock_page.title.return_value = "Example Domain"
        browser._page = mock_page

        with patch.object(browser, "_ensure_page", return_value=mock_page):
            settle_res = browser.wait_for_settle(timeout_ms=500, wait_for_network=False)
            assert settle_res["success"] is True
            assert settle_res["settled"] is True
            assert "duration_ms" in settle_res

        with patch("extra.fastpath.browser.get_browser_fastpath", return_value=browser):
            res = execute_browser_action(action="settle", value="1000")
            assert res["success"] is True
            assert res["settled"] is True


class TestTieredVerificationPhase3:
    """Test suite for Tier 3 milestone verification, SOUL-Critic bridge, and auto-rollback."""

    def test_milestone_verifier_with_soul_critic_pass(self) -> None:
        """Verifies MilestoneVerifier passes when SOUL-Critic confirms required visual elements."""
        from extra.core.composer.blueprint import Milestone
        from extra.core.composer.verifier import MilestoneVerifier
        from extra.core.soul.critic import CriticVerdict

        m = Milestone(
            id="M1_CANVAS",
            name="Initialize Canvas",
            expected_artifacts=[],
            acceptance_criteria={
                "expected_elements": ["Design Canvas", "Tools Rail"],
                "unwanted_elements": ["Crash"],
            },
        )

        verifier = MilestoneVerifier()
        mock_verdict = CriticVerdict(
            passed=True,
            confidence=0.92,
            defects=[],
            latency_ms=120.0,
        )

        with patch("extra.core.soul.critic.SoulCritic.evaluate_screen_milestone", return_value=mock_verdict):
            res = verifier.verify_milestone(m)
            assert res.passed is True
            assert len(res.defects) == 0

    def test_milestone_verifier_with_soul_critic_fail_defect(self) -> None:
        """Verifies MilestoneVerifier records defects when SOUL-Critic identifies failures."""
        from extra.core.composer.blueprint import Milestone
        from extra.core.composer.verifier import MilestoneVerifier
        from extra.core.soul.critic import CriticVerdict

        m = Milestone(
            id="M2_RENDER",
            name="Export Video",
            expected_artifacts=[],
            acceptance_criteria={
                "expected_elements": ["Export Complete"],
            },
        )

        verifier = MilestoneVerifier()
        mock_verdict = CriticVerdict(
            passed=False,
            confidence=0.3,
            defects=["Required element 'Export Complete' not found on screen"],
            latency_ms=95.0,
        )

        with patch("extra.core.soul.critic.SoulCritic.evaluate_screen_milestone", return_value=mock_verdict):
            res = verifier.verify_milestone(m)
            assert res.passed is False
            assert any("Export Complete" in d for d in res.defects)

    def test_blueprint_milestone_auto_rollback_on_failure(self) -> None:
        """Verifies auto_rollback=True rolls back downstream milestones on verification failure."""
        from extra.core.composer.blueprint import Milestone, TaskBlueprint
        from extra.core.composer.verifier import VerificationResult
        from extra.mcp.server import _active_blueprints, extra_blueprint_milestone

        m1 = Milestone(id="M1", name="Step 1")
        m2 = Milestone(id="M2", name="Step 2", dependencies=["M1"])
        bp = TaskBlueprint(title="Test Task", milestones=[m1, m2])
        _active_blueprints[bp.task_id] = bp

        # Start M1 then M2
        bp.start_milestone("M1")
        bp.complete_milestone("M1")
        bp.start_milestone("M2")

        failed_verif = VerificationResult(
            passed=False,
            defects=["Artifact missing: out.mp4"],
        )

        with patch("extra.mcp.server.verify_milestone_acceptance", return_value=failed_verif):
            res = extra_blueprint_milestone(
                task_id=bp.task_id,
                milestone_id="M2",
                action="complete",
                auto_rollback=True,
            )
            assert res["success"] is False
            assert res["verified"] is False
            assert res["auto_rollback"] is True
            assert "M2" in res["reset_milestones"]
            assert bp.milestones["M2"].status.value == "pending"

    def test_hipif_dense_token_generation_after_verification(self) -> None:
        """Verifies successful milestone completion produces a compact HIPIF semantic state token."""
        from extra.core.composer.blueprint import Milestone, TaskBlueprint
        from extra.core.composer.verifier import VerificationResult
        from extra.mcp.server import _active_blueprints, extra_blueprint_milestone

        m1 = Milestone(id="M1_INIT", name="Initial Setup")
        bp = TaskBlueprint(title="Setup Pipeline", milestones=[m1])
        _active_blueprints[bp.task_id] = bp
        bp.start_milestone("M1_INIT")

        pass_verif = VerificationResult(passed=True, defects=[])

        with patch("extra.mcp.server.verify_milestone_acceptance", return_value=pass_verif):
            res = extra_blueprint_milestone(
                task_id=bp.task_id,
                milestone_id="M1_INIT",
                action="complete",
                summary="Project initialized with 1080p canvas",
            )
            assert res["success"] is True
            assert res["verified"] is True
            assert "state_token" in res
            assert "M1_INIT" in res["state_token"]
            assert res["is_task_complete"] is True


