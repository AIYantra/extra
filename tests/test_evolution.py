"""
Unit tests for Extra Evolution subsystem (analyzer, crystallizer, curator).
"""

import os
import unittest
from pathlib import Path

from extra.core.evolution.analyzer import analyze_task_trajectory
from extra.core.evolution.crystallizer import crystallize_skill_evolution
from extra.core.evolution.curator import curate_skill_library


class TestExtraEvolution(unittest.TestCase):
    def test_trajectory_clean_path(self):
        """Tests that clean fast-path trajectories are flagged without friction."""
        events = [
            {"tool_name": "extra_launch", "app_name": "calc", "duration_ms": 100},
            {"tool_name": "extra_type", "text": "100+250=", "duration_ms": 10},
            {"tool_name": "extra_screenshot", "duration_ms": 15},
        ]
        analysis = analyze_task_trajectory(task_id="clean_task_1", events=events, success=True)
        self.assertFalse(analysis.friction_detected)
        self.assertFalse(analysis.candidate_for_evolution)
        self.assertEqual(analysis.stall_count, 0)

    def test_trajectory_friction_and_stall(self):
        """Tests that stalls and repetitive hunting trigger evolution candidacy."""
        events = [
            {"tool_name": "extra_launch", "app_name": "canva", "duration_ms": 200},
            {"tool_name": "extra_screenshot", "duration_ms": 20},
            {"tool_name": "extra_click", "x": 100, "y": 200, "duration_ms": 15},
            {"tool_name": "extra_click", "x": 102, "y": 201, "duration_ms": 15},
            {"tool_name": "extra_click", "x": 101, "y": 202, "duration_ms": 15},
            {"tool_name": "extra_screenshot", "duration_ms": 20},
            {"type": "stall", "trigger_action": "StallBreaker strike: 3 failed clicks", "duration_ms": 50},
            {"tool_name": "extra_type", "text": "resolving action", "duration_ms": 10},
        ]
        analysis = analyze_task_trajectory(task_id="stalled_task_1", events=events, success=True)
        self.assertTrue(analysis.friction_detected)
        self.assertTrue(analysis.candidate_for_evolution)
        self.assertEqual(analysis.stall_count, 1)
        self.assertIn("Stall detected", analysis.friction_reasons[0])

    def test_crystallize_skill_evolution(self):
        """Tests crystallizing a discovered fast path into an evolved skill."""
        res = crystallize_skill_evolution(
            app_name="canva",
            workflow_summary="Direct Instagram Poster Fast Path",
            instructions="Generate PNG with PIL to .extra/workspace, copy with PowerShell STA, focus Canva, press Ctrl+V.",
            friction_points=["Clicking template search cards stalls repeatedly due to WebGL canvas."],
            solutions_found=["Inject PNG directly via clipboard."],
        )
        self.assertEqual(res["status"], "evolved")
        self.assertEqual(res["app_name"], "canva")
        self.assertTrue(len(res["skill_paths"]) > 0)

        # Verify content in generated file
        skill_file = Path(res["skill_paths"][0])
        self.assertTrue(skill_file.exists())
        content = skill_file.read_text(encoding="utf-8")
        self.assertIn("Direct Instagram Poster Fast Path", content)
        self.assertIn("Inject PNG directly via clipboard", content)
        self.assertIn("Extra Evolution Engine", content)

    def test_curate_skill_library(self):
        """Tests library curation and auditing across workspace and global paths."""
        audit = curate_skill_library()
        self.assertIn("total_unique_skills", audit)
        self.assertGreater(audit["total_unique_skills"], 0)
        self.assertIn("skills", audit)


if __name__ == "__main__":
    unittest.main()
