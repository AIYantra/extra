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
        """Tests crystallizing a discovered fast path into an evolved skill in an isolated directory."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "extra-mockapp"
            res = crystallize_skill_evolution(
                app_name="mockapp",
                workflow_summary="Direct Automated Fast Path",
                instructions="Generate asset programmatically and execute zero-stall fast path.",
                friction_points=["Clicking template search cards stalls repeatedly."],
                solutions_found=["Inject asset directly via clipboard."],
                target_dirs=[target],
            )
            self.assertEqual(res["status"], "evolved")
            self.assertEqual(res["app_name"], "mockapp")
            self.assertTrue(len(res["skill_paths"]) > 0)

            # Verify content in generated file
            skill_file = Path(res["skill_paths"][0])
            self.assertTrue(skill_file.exists())
            content = skill_file.read_text(encoding="utf-8")
            self.assertIn("Direct Automated Fast Path", content)
            self.assertIn("Inject asset directly via clipboard", content)
            self.assertIn("Extra Evolution Engine", content)


    def test_trajectory_thrashing_not_golden_path(self):
        """Tests that trajectories with undo actions and heavy stalls are not flagged as clean golden paths."""
        events = [
            {"tool_name": "extra_launch", "app_name": "canva", "duration_ms": 200},
            {"tool_name": "extra_hotkey", "keys": ["ctrl", "z"], "duration_ms": 10},
            {"tool_name": "extra_hotkey", "keys": ["ctrl", "z"], "duration_ms": 10},
            {"type": "stall", "trigger_action": "StallBreaker strike", "duration_ms": 50},
            {"type": "stall", "trigger_action": "StallBreaker strike", "duration_ms": 50},
            {"tool_name": "extra_type", "text": "recovered", "duration_ms": 10},
        ]
        analysis = analyze_task_trajectory(task_id="thrashing_task_1", events=events, success=True)
        self.assertTrue(analysis.friction_detected)
        self.assertFalse(analysis.is_golden_path)
        self.assertTrue(analysis.candidate_for_evolution)
        self.assertIn("not a clean golden path", analysis.suggested_playbook)

    def test_crystallizer_strict_deduplication(self):
        """Tests that repeatedly crystallizing identical friction points and solutions never produces duplicate lines."""
        from extra.core.evolution.crystallizer import _patch_skill_content
        base_skill = (
            "---\nname: extra-test\ndescription: Test skill.\n---\n"
            "# Test Automation Protocol\n\n"
            "## 2. Zero-Stall Fast Paths\n"
            "## 5. Anti-Stall Guardrails & Caveats\n"
        )
        
        # Patch once
        patched_1 = _patch_skill_content(
            content=base_skill,
            workflow_summary="Test Workflow",
            instructions="Execute test step.",
            friction_points=["Test pitfall detected."],
            solutions_found=["Test resolution applied."],
        )
        self.assertEqual(patched_1.count("- Avoid: Test pitfall detected."), 1)
        self.assertEqual(patched_1.count("- Verified Resolution: Test resolution applied."), 1)
        self.assertEqual(patched_1.count("<!-- Evolved by Extra Evolution Engine:"), 1)

        # Patch again with the EXACT SAME inputs
        patched_2 = _patch_skill_content(
            content=patched_1,
            workflow_summary="Test Workflow",
            instructions="Execute test step.",
            friction_points=["Test pitfall detected."],
            solutions_found=["Test resolution applied."],
        )
        # Invariants: counts MUST remain strictly 1
        self.assertEqual(patched_2.count("- Avoid: Test pitfall detected."), 1)
        self.assertEqual(patched_2.count("- Verified Resolution: Test resolution applied."), 1)
        self.assertEqual(patched_2.count("- **Evolved Fast Path (Test Workflow):**"), 1)
        self.assertEqual(patched_2.count("<!-- Evolved by Extra Evolution Engine:"), 1)
        self.assertEqual(patched_1, patched_2)

    def test_curate_skill_library(self):
        """Tests library curation and auditing across workspace and global paths."""
        audit = curate_skill_library()
        self.assertIn("total_unique_skills", audit)
        self.assertGreater(audit["total_unique_skills"], 0)
        self.assertIn("skills", audit)

    def test_crystallizer_non_golden_path_guardrails_only(self):
        """Tests that non-golden paths only update guardrails and do not inject into Zero-Stall Fast Paths."""
        from extra.core.evolution.crystallizer import _patch_skill_content
        base_skill = (
            "---\nname: extra-test\ndescription: Test skill.\n---\n"
            "# Test Automation Protocol\n\n"
            "## 2. Zero-Stall Fast Paths\n"
            "## 5. Anti-Stall Guardrails & Caveats\n"
        )
        patched = _patch_skill_content(
            content=base_skill,
            workflow_summary="Noisy Stalled Workflow",
            instructions="Do step 1, stall, retry 5 times, then finish.",
            friction_points=["Stalled repeatedly on element X."],
            solutions_found=["Use keyboard shortcut instead."],
            is_golden_path=False,
        )
        # Invariant: fast paths section must NOT contain the noisy instructions
        self.assertNotIn("Noisy Stalled Workflow", patched.split("## 5. Anti-Stall Guardrails & Caveats")[0])
        # Invariant: guardrails section must contain the pitfall and solution
        self.assertIn("- Avoid: Stalled repeatedly on element X.", patched)
        self.assertIn("- Verified Resolution: Use keyboard shortcut instead.", patched)


    def test_trajectory_undo_in_batch_actions_never_golden_path(self):
        """Tests that any undo action (even in batch actions) strictly disqualifies golden path."""
        events = [
            {"tool_name": "extra_launch", "app_name": "canva", "duration_ms": 200},
            {"tool_name": "extra_batch_actions", "actions": [{"action": "hotkey", "keys": ["ctrl", "z"]}], "duration_ms": 15},
            {"tool_name": "extra_screenshot", "duration_ms": 20},
        ]
        analysis = analyze_task_trajectory(task_id="undo_batch_task", events=events, success=True)
        self.assertEqual(analysis.undo_count, 1)
        self.assertTrue(analysis.friction_detected)
        self.assertFalse(analysis.is_golden_path)
        self.assertTrue(analysis.candidate_for_evolution)
        self.assertIn("not a clean golden path", analysis.suggested_playbook)

    def test_sanitize_skill_library(self):
        """Tests that sanitize_skill_library removes mock skills and purges legacy evolved fast paths."""
        import tempfile
        from extra.core.evolution.curator import sanitize_skill_library
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            # Create a mock skill directory
            mock_dir = base / "extra-mock-app"
            mock_dir.mkdir(parents=True, exist_ok=True)
            (mock_dir / "SKILL.md").write_text("---\nname: extra-mock-app\ndescription: Mock\n---\n# Mock", encoding="utf-8")

            # Create a skill with contaminated evolved lines
            real_dir = base / "extra-testapp"
            real_dir.mkdir(parents=True, exist_ok=True)
            contaminated = (
                "---\nname: extra-testapp\ndescription: Test Playbook\n---\n"
                "# TestApp Protocol\n\n"
                "## 2. Zero-Stall Fast Paths\n"
                "- **Evolved Fast Path (Failed Workflow):** Some noisy recovery steps.\n"
                "- **Native Template Fast-Path:** Legitimate base path.\n\n"
                "## 5. Anti-Stall Guardrails & Caveats\n"
                "- Avoid: Stalling.\n"
                "<!-- Evolved by Extra Evolution Engine: 2026-09-24 10:00:00 | Focus: Failed Workflow -->\n"
            )
            (real_dir / "SKILL.md").write_text(contaminated, encoding="utf-8")

            report = sanitize_skill_library(strip_legacy_evolved=True, remove_mock_skills=True, target_dirs=[base])
            self.assertEqual(report["status"], "success")
            self.assertEqual(report["files_cleaned"], 1)
            self.assertEqual(len(report["mocks_removed"]), 1)
            self.assertFalse(mock_dir.exists())

            cleaned_content = (real_dir / "SKILL.md").read_text(encoding="utf-8")
            self.assertNotIn("Evolved Fast Path", cleaned_content)
            self.assertNotIn("Extra Evolution Engine", cleaned_content)
            self.assertIn("Native Template Fast-Path", cleaned_content)
            self.assertIn("Avoid: Stalling", cleaned_content)

    def test_ensure_startup_migration(self):
        """Tests startup migration marker check and execution."""
        from extra.core.evolution.curator import ensure_startup_migration
        marker_file = Path.home() / ".extra" / ".v0_3_0_migration_done"
        res = ensure_startup_migration()
        self.assertIn(res.get("status"), ["already_migrated", "migrated"])
        self.assertTrue(marker_file.exists())


if __name__ == "__main__":
    unittest.main()


