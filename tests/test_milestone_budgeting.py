"""
Exhaustive Test Suite for Milestone Turn Budgeting & Task Blueprint Pacing.
Validates:
1. Milestone default turn budget (max_turns=30) and properties (remaining_turns, is_budget_exceeded).
2. Serialization & deserialization resilience in to_dict() and from_dict().
3. TaskBlueprint.record_milestone_turn() tracking and warning triggers on budget overflow.
4. TaskBlueprint.get_budget_status() diagnostics across multiple milestones.
5. MCP tools (extra_blueprint_start, extra_blueprint_milestone) handling record_turn and status actions.
6. Automatic turn tracking integration via _track_active_blueprint_turn().
"""

import os
import unittest
from extra.core.composer.blueprint import Milestone, MilestoneStatus, TaskBlueprint
from extra.mcp.server import (
    _active_blueprints,
    _track_active_blueprint_turn,
    extra_blueprint_milestone,
    extra_blueprint_start,
)


class TestMilestoneBudgeting(unittest.TestCase):
    """Tests for Milestone turn budget defaults and tracking."""

    def test_milestone_budget_defaults(self):
        m = Milestone(id="m1", name="Prepare Data")
        self.assertEqual(m.max_turns, 30)
        self.assertEqual(m.turns_consumed, 0)
        self.assertEqual(m.remaining_turns, 30)
        self.assertFalse(m.is_budget_exceeded)

    def test_milestone_budget_properties(self):
        m = Milestone(id="m1", name="Prepare Data", max_turns=10, turns_consumed=7)
        self.assertEqual(m.remaining_turns, 3)
        self.assertFalse(m.is_budget_exceeded)

        m.turns_consumed = 10
        self.assertEqual(m.remaining_turns, 0)
        self.assertTrue(m.is_budget_exceeded)

        m.turns_consumed = 15
        self.assertEqual(m.remaining_turns, 0)
        self.assertTrue(m.is_budget_exceeded)

    def test_milestone_serialization_and_deserialization(self):
        m = Milestone(id="m1", name="Step 1", max_turns=25, turns_consumed=12)
        d = m.to_dict()
        self.assertEqual(d["max_turns"], 25)
        self.assertEqual(d["turns_consumed"], 12)
        self.assertEqual(d["remaining_turns"], 13)
        self.assertFalse(d["is_budget_exceeded"])

        # Roundtrip from_dict
        restored = Milestone.from_dict(d)
        self.assertEqual(restored.max_turns, 25)
        self.assertEqual(restored.turns_consumed, 12)
        self.assertEqual(restored.remaining_turns, 13)

        # Fallback when max_turns is invalid or None
        fallback = Milestone.from_dict({"id": "m2", "name": "Step 2", "max_turns": -5})
        self.assertEqual(fallback.max_turns, 30)


class TestTaskBlueprintBudgeting(unittest.TestCase):
    """Tests for TaskBlueprint turn tracking, budget status, and warning generation."""

    def setUp(self):
        self.m1 = Milestone(id="m1", name="Step 1", max_turns=5)
        self.m2 = Milestone(id="m2", name="Step 2", dependencies=["m1"], max_turns=10)
        self.bp = TaskBlueprint(title="Test Task", milestones=[self.m1, self.m2])

    def test_record_turn_within_budget(self):
        self.bp.start_milestone("m1")
        res = self.bp.record_milestone_turn("m1", turns=2)
        self.assertEqual(res["turns_consumed"], 2)
        self.assertEqual(res["max_turns"], 5)
        self.assertEqual(res["remaining_turns"], 3)
        self.assertFalse(res["budget_exceeded"])
        self.assertIsNone(res["warning"])

    def test_record_turn_exceeds_budget(self):
        self.bp.start_milestone("m1")
        # Consume 5 turns
        self.bp.record_milestone_turn("m1", turns=5)
        self.assertTrue(self.m1.is_budget_exceeded)

        # Consume 1 more turn
        res = self.bp.record_milestone_turn("m1", turns=1)
        self.assertEqual(res["turns_consumed"], 6)
        self.assertTrue(res["budget_exceeded"])
        self.assertIsNotNone(res["warning"])
        self.assertIn("BUDGET_OVERFLOW", res["warning"])

    def test_get_budget_status(self):
        self.bp.start_milestone("m1")
        self.bp.record_milestone_turn("m1", turns=6)
        status = self.bp.get_budget_status()

        self.assertEqual(status["total_milestones"], 2)
        self.assertEqual(status["total_max_turns"], 15)
        self.assertEqual(status["total_turns_consumed"], 6)
        self.assertEqual(status["over_budget_count"], 1)
        self.assertIn("m1", status["over_budget_milestones"])
        self.assertTrue(status["milestones"]["m1"]["budget_exceeded"])
        self.assertFalse(status["milestones"]["m2"]["budget_exceeded"])


class TestMCPBlueprintMilestoneTools(unittest.TestCase):
    """Tests for MCP server blueprint tools with turn budget integration."""

    def setUp(self):
        _active_blueprints.clear()

    def tearDown(self):
        _active_blueprints.clear()

    def test_mcp_blueprint_lifecycle_and_turn_tracking(self):
        # 1. Start blueprint
        start_res = extra_blueprint_start(
            title="Multi-App Pipeline",
            task_type="general",
            milestones=[
                {"id": "m1", "name": "Notepad Briefing", "max_turns": 3},
                {"id": "m2", "name": "Calc Analysis", "dependencies": ["m1"], "max_turns": 5},
            ],
        )
        self.assertTrue(start_res["success"])
        task_id = start_res["task_id"]
        self.assertIn("budget_status", start_res)

        # 2. Start milestone m1
        m1_start = extra_blueprint_milestone(task_id=task_id, milestone_id="m1", action="start")
        self.assertTrue(m1_start["success"])
        self.assertEqual(m1_start["max_turns"], 3)
        self.assertEqual(m1_start["remaining_turns"], 3)

        # 3. Explicit record_turn
        t1 = extra_blueprint_milestone(task_id=task_id, milestone_id="m1", action="record_turn")
        self.assertTrue(t1["success"])
        self.assertEqual(t1["turns_consumed"], 1)
        self.assertEqual(t1["remaining_turns"], 2)
        self.assertFalse(t1["budget_exceeded"])

        # 4. Automatic turn tracking via _track_active_blueprint_turn
        warn1 = _track_active_blueprint_turn()
        self.assertIsNone(warn1)  # turns_consumed is now 2 / 3

        warn2 = _track_active_blueprint_turn()
        self.assertIsNotNone(warn2)  # turns_consumed is now 3 / 3 (budget reached)
        self.assertIn("BUDGET_OVERFLOW", warn2)

        # 5. Check budget status via MCP
        status = extra_blueprint_milestone(task_id=task_id, milestone_id="m1", action="status")
        self.assertTrue(status["success"])
        self.assertEqual(status["total_turns_consumed"], 3)
        self.assertEqual(status["over_budget_count"], 1)

        # 6. Complete milestone m1
        comp = extra_blueprint_milestone(task_id=task_id, milestone_id="m1", action="complete")
        self.assertTrue(comp["success"])
        self.assertTrue(comp["budget_exceeded"])
        self.assertIsNotNone(comp["budget_warning"])


if __name__ == "__main__":
    unittest.main()
