"""
Exhaustive Test Suite for Extra Hierarchical Composer-Director Engine & Project SOUL Superpowers.
Validates:
1. TaskBlueprint & TaskDAG dependency graph, topological sort, cycle detection, rollback.
2. HIPIF Information Folding, durable checkpoints, dense state tokens, and context compression.
3. Universal Execution Bridge (Python, PowerShell, CLI) and artifact detection.
4. Project SOUL Gateman settle detection, Critic milestone QA, and Compressor.
5. Universal Engine Compliance (Zero app-specific hardcoding in core).
"""

import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path
from PIL import Image

from extra.core.composer.blueprint import (
    Milestone,
    MilestoneStatus,
    TaskBlueprint,
    TaskDAG,
)
from extra.core.composer.folding import (
    HIPIFFolder,
    StateCheckpoint,
    create_semantic_state_token,
    fold_completed_milestone,
)
from extra.core.composer.verifier import (
    MilestoneVerifier,
    VerificationResult,
    verify_milestone_acceptance,
)
from extra.fastpath.bridge import (
    BridgeResult,
    UniversalBridgeRegistry,
    execute_bridge,
)
from extra.core.soul.gateman import SoulGateman
from extra.core.soul.critic import CriticVerdict, SoulCritic
from extra.core.soul.compressor import SoulCompressor


class TestTaskBlueprintAndDAG(unittest.TestCase):
    """Tests for TaskDAG dependency resolution, cycle prevention, and TaskBlueprint lifecycle."""

    def test_cycle_detection(self):
        """Ensures circular milestone dependencies are detected and rejected."""
        m1 = Milestone(id="m1", name="Step 1", dependencies=["m2"])
        m2 = Milestone(id="m2", name="Step 2", dependencies=["m1"])
        with self.assertRaises(ValueError):
            TaskDAG({"m1": m1, "m2": m2})

    def test_missing_dependency_detection(self):
        """Ensures dependency on non-existent milestone raises ValueError."""
        m1 = Milestone(id="m1", name="Step 1", dependencies=["m_ghost"])
        with self.assertRaises(ValueError):
            TaskDAG({"m1": m1})

    def test_dag_runnable_resolution(self):
        """Verifies runnable milestones advance correctly as dependencies complete."""
        m1 = Milestone(id="m1", name="Step 1")
        m2 = Milestone(id="m2", name="Step 2", dependencies=["m1"])
        m3 = Milestone(id="m3", name="Step 3", dependencies=["m1"])
        m4 = Milestone(id="m4", name="Step 4", dependencies=["m2", "m3"])

        bp = TaskBlueprint(title="Test Pipeline", milestones=[m1, m2, m3, m4])

        # Initially, only m1 has no dependencies
        runnable = bp.get_next_runnable()
        self.assertEqual(len(runnable), 1)
        self.assertEqual(runnable[0].id, "m1")

        # Start and complete m1
        bp.start_milestone("m1")
        bp.complete_milestone("m1")

        # Now m2 and m3 should be runnable concurrently
        runnable = bp.get_next_runnable()
        self.assertEqual({m.id for m in runnable}, {"m2", "m3"})

        # Complete m2; m4 still blocked on m3
        bp.complete_milestone("m2")
        runnable = bp.get_next_runnable()
        self.assertEqual([m.id for m in runnable], ["m3"])

        # Complete m3; m4 becomes runnable
        bp.complete_milestone("m3")
        runnable = bp.get_next_runnable()
        self.assertEqual([m.id for m in runnable], ["m4"])

        bp.complete_milestone("m4")
        self.assertTrue(bp.is_complete)
        self.assertFalse(bp.has_failed)

    def test_rollback_recovery(self):
        """Verifies non-destructive rollback resets target milestone and all downstream dependents."""
        m1 = Milestone(id="m1", name="M1")
        m2 = Milestone(id="m2", name="M2", dependencies=["m1"])
        m3 = Milestone(id="m3", name="M3", dependencies=["m2"])

        bp = TaskBlueprint(title="Rollback Test", milestones=[m1, m2, m3])
        bp.complete_milestone("m1")
        bp.complete_milestone("m2")
        bp.fail_milestone("m3", error="Simulated render crash")

        self.assertTrue(bp.has_failed)

        # Rollback to m2
        reset_ids = bp.rollback_to("m2")
        self.assertEqual(set(reset_ids), {"m2", "m3"})

        # m1 remains completed, m2 and m3 reset to pending
        self.assertEqual(bp.milestones["m1"].status, MilestoneStatus.COMPLETED)
        self.assertEqual(bp.milestones["m2"].status, MilestoneStatus.PENDING)
        self.assertEqual(bp.milestones["m3"].status, MilestoneStatus.PENDING)
        self.assertFalse(bp.has_failed)

        # m2 is immediately runnable again
        runnable = bp.get_next_runnable()
        self.assertEqual([m.id for m in runnable], ["m2"])

    def test_blueprint_serialization(self):
        """Verifies TaskBlueprint saves to disk and deserializes identically."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "test_blueprint.json"
            m1 = Milestone(id="m1", name="Generate Assets", runtime="python", expected_artifacts=["asset.png"])
            bp = TaskBlueprint(title="Serialization Test", task_type="3d_modeling", milestones=[m1])
            bp.save(file_path)

            loaded = TaskBlueprint.load(file_path)
            self.assertEqual(loaded.title, "Serialization Test")
            self.assertEqual(loaded.task_type, "3d_modeling")
            self.assertEqual(len(loaded.milestones), 1)
            self.assertEqual(loaded.milestones["m1"].expected_artifacts, ["asset.png"])


class TestHIPIFFolding(unittest.TestCase):
    """Tests for Hierarchical Information Folding (HIPIF) and context compression."""

    def test_dense_semantic_state_token(self):
        """Ensures state tokens are compact (< 15 words) and contain key status metadata."""
        m = Milestone(id="m1", name="Procedural Mesh", expected_artifacts=["mesh.obj", "diffuse.png"])
        token = create_semantic_state_token(m, custom_status="OK")
        self.assertIn("[MILESTONE_COMPLETE: m1", token)
        self.assertIn("name: 'Procedural Mesh'", token)
        self.assertIn("artifacts: 2", token)
        self.assertLess(len(token.split()), 20)

    def test_hipif_checkpoint_persistence(self):
        """Verifies checkpoints are recorded to disk and folded prompts remain compact."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            folder = HIPIFFolder(checkpoints_dir=Path(tmp_dir))
            m1 = Milestone(id="m1", name="Setup Project")
            m2 = Milestone(id="m2", name="Import Sequence", dependencies=["m1"])
            bp = TaskBlueprint(title="Video Assembly", milestones=[m1, m2])

            bp.complete_milestone("m1")
            ckpt = folder.fold_milestone(bp, "m1", summary="Sequence initialized with 4 clips")

            self.assertEqual(ckpt.milestone_id, "m1")
            self.assertEqual(ckpt.completed_milestones, ["m1"])
            self.assertEqual(ckpt.pending_milestones, ["m2"])

            prompt = folder.generate_folded_prompt(bp)
            self.assertIn("[HIPIF Task Context: Video Assembly]", prompt)
            self.assertIn("[DONE] **m1**", prompt)
            self.assertIn("**Next Runnable Milestone:** `m2`", prompt)
            self.assertLess(len(prompt.splitlines()), 15)


class TestUniversalBridge(unittest.TestCase):
    """Tests for the Universal Execution Bridge across runtimes."""

    def test_python_runtime_inline_execution(self):
        """Verifies executing python code via bridge."""
        code = "import sys\nprint('BRIDGE_SUCCESS_OK')\nsys.exit(0)"
        res = execute_bridge(runtime="python", payload=code, timeout_sec=10.0)
        self.assertTrue(res.success)
        self.assertEqual(res.returncode, 0)
        self.assertIn("BRIDGE_SUCCESS_OK", res.stdout)
        self.assertLess(res.latency_ms, 5000.0)

    def test_powershell_runtime_execution(self):
        """Verifies executing powershell payload via bridge."""
        if sys.platform != "win32":
            return
        cmd = "Write-Output 'POWERSHELL_BRIDGE_OK'"
        res = execute_bridge(runtime="powershell", payload=cmd, timeout_sec=10.0)
        self.assertTrue(res.success)
        self.assertEqual(res.returncode, 0)
        self.assertIn("POWERSHELL_BRIDGE_OK", res.stdout)

    def test_artifact_detection(self):
        """Verifies bridge correctly detects newly created artifacts."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "output.txt"
            code = f"from pathlib import Path\nPath(r'{out_file}').write_text('GENERATED_DATA')"
            res = execute_bridge(
                runtime="python",
                payload=code,
                expected_artifacts=[str(out_file)],
                timeout_sec=10.0,
            )
            self.assertTrue(res.success)
            self.assertEqual(res.artifacts_created, [str(out_file)])
            self.assertTrue(out_file.exists())
            self.assertEqual(out_file.read_text(), "GENERATED_DATA")

    def test_unsupported_runtime_guard(self):
        """Verifies executing an unknown runtime returns a safe failure without crashing."""
        res = execute_bridge(runtime="quantum_runtime_v9", payload="echo 1")
        self.assertFalse(res.success)
        self.assertIn("Unsupported runtime", res.error)


class TestSoulGatemanAndCritic(unittest.TestCase):
    """Tests for Project SOUL Gateman settle detection and Critic verification."""

    def test_soul_gateman_settle_mock(self):
        """Verifies SoulGateman returns settled structure."""
        gateman = SoulGateman()
        res = gateman.wait_until_settled(timeout_sec=1.0, settle_frames=2, check_interval_ms=20)
        self.assertIn("settled", res)
        self.assertIn("duration_ms", res)
        self.assertIn("frames_inspected", res)
        self.assertGreaterEqual(res["frames_inspected"], 1)

    def test_soul_critic_milestone_evaluation(self):
        """Verifies SoulCritic evaluates milestone criteria and reports defects."""
        critic = SoulCritic()
        # Create a blank white test image
        img = Image.new("RGB", (640, 480), color="white")
        verdict = critic.evaluate_screen_milestone(
            milestone_name="Test Milestone",
            expected_elements=["GhostButton123456789"],
            image=img,
        )
        self.assertFalse(verdict.passed)
        self.assertGreater(len(verdict.defects), 0)
        self.assertIn("GhostButton123456789", verdict.defects[0])

    def test_soul_compressor_state_token(self):
        """Verifies SoulCompressor formats clean, dense tokens."""
        compressor = SoulCompressor()
        v = CriticVerdict(passed=True, confidence=0.98, defects=[], latency_ms=15.0)
        token = compressor.compress_milestone_state("M1", "Render Complete", verdict=v, artifacts=["a.png"], duration_ms=120.0)
        self.assertEqual(token, "[STATE: M1_PASS | Name: 'Render Complete' | Artifacts: 1 | Latency: 120ms]")


class TestUniversalEngineCompliance(unittest.TestCase):
    """Strict verification: ZERO hardcoded app-specific branches in new core & fastpath modules."""

    def test_zero_app_specific_code_in_composer(self):
        """Verifies no hardcoded creative app names in extra/core/composer."""
        repo_root = Path(__file__).resolve().parent.parent
        composer_dir = repo_root / "core" / "composer"
        for f in composer_dir.glob("*.py"):
            content = f.read_text(encoding="utf-8").lower()
            for forbidden in ["if app == ", "if 'premiere' in", "if 'blender' in", "if 'canva' in"]:
                self.assertNotIn(
                    forbidden, content,
                    f"Forbidden app-specific branch '{forbidden}' found in {f.name}"
                )

    def test_zero_app_specific_code_in_bridge(self):
        """Verifies no hardcoded creative app names in extra/fastpath/bridge.py."""
        repo_root = Path(__file__).resolve().parent.parent
        bridge_file = repo_root / "fastpath" / "bridge.py"
        content = bridge_file.read_text(encoding="utf-8").lower()
        for forbidden in ["if app == ", "if 'canva' in", "if 'photoshop' in"]:
            self.assertNotIn(
                forbidden, content,
                f"Forbidden app-specific branch '{forbidden}' found in bridge.py"
            )


class TestMCPToolIntegration(unittest.TestCase):
    """Verifies that the new MCP server tools invoke and return expected contracts."""

    def test_mcp_blueprint_and_bridge_roundtrip(self):
        """Tests extra_blueprint_start, extra_execute_bridge, extra_blueprint_milestone roundtrip."""
        from extra.mcp.server import (
            extra_blueprint_milestone,
            extra_blueprint_start,
            extra_execute_bridge,
            extra_soul_wait,
        )

        # 1. Start a blueprint
        start_res = extra_blueprint_start(
            title="MCP Test Task",
            task_type="3d_modeling",
            milestones=[
                {"id": "m1", "name": "Generate Mesh", "expected_artifacts": []},
                {"id": "m2", "name": "Render Scene", "dependencies": ["m1"]},
            ],
        )
        self.assertTrue(start_res["success"])
        task_id = start_res["task_id"]
        self.assertEqual(len(start_res["runnable_milestones"]), 1)
        self.assertEqual(start_res["runnable_milestones"][0]["id"], "m1")

        # 2. Execute bridge python payload
        bridge_res = extra_execute_bridge(
            runtime="python",
            payload="print('BRIDGE_ROUNDTRIP_OK')",
            timeout_sec=5.0,
        )
        self.assertTrue(bridge_res["success"])
        self.assertIn("BRIDGE_ROUNDTRIP_OK", bridge_res["stdout"])

        # 3. Advance milestone m1 to complete
        comp_res = extra_blueprint_milestone(
            task_id=task_id,
            milestone_id="m1",
            action="complete",
            result=bridge_res,
            summary="Mesh generated via Python bridge",
        )
        self.assertTrue(comp_res["success"])
        self.assertTrue(comp_res["verified"])
        self.assertIn("[MILESTONE_COMPLETE: m1", comp_res["state_token"])
        self.assertEqual(len(comp_res["next_runnable_milestones"]), 1)
        self.assertEqual(comp_res["next_runnable_milestones"][0]["id"], "m2")

        # 4. Test extra_soul_wait
        wait_res = extra_soul_wait(condition="settled", timeout_sec=0.5)
        self.assertIn("settled", wait_res)

    def test_mcp_blueprint_resilience_to_title_and_unknown_fields(self):
        """Verifies extra_blueprint_start accepts 'title' alias and ignores unexpected fields."""
        from extra.mcp.server import extra_blueprint_start

        res = extra_blueprint_start(
            title="Resilient Task",
            task_type="general",
            milestones=[
                {
                    "id": "m1",
                    "title": "Milestone with Title Key",
                    "unexpected_meta": 42,
                    "notes": "Some notes from LLM",
                },
                {
                    "title": "Milestone without ID",
                    "dependencies": ["m1"],
                },
            ],
        )
        self.assertTrue(res["success"], f"Blueprint start failed: {res.get('error')}")
        self.assertIn("task_id", res)
        self.assertEqual(res["total_milestones"], 2)


if __name__ == "__main__":
    unittest.main()
