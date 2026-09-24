"""
Unit Tests for Project SOUL — Phase 5: Self-Evolution & Memory Distillation
Validates trajectory mining, KùzuDB decision logging, sub-2ms prior recall,
and skill crystallization of SOUL fast paths.
"""

import shutil
import tempfile
import time
import unittest
from pathlib import Path

from extra.core.evolution.crystallizer import crystallize_soul_fastpath
from extra.core.memory.db import close_memory_db, get_memory_connection, get_memory_db
from extra.core.memory.ingest import (
    TaskMemoryRecorder,
    finish_memory_recording,
    get_active_recorder,
    record_action_soul_decision,
    start_memory_recording,
)
from extra.core.memory.recall import recall_memory, recall_soul_decision
from extra.core.soul.decider import SoulDecider, get_soul_decider
from extra.core.soul.schemas import DecisionType


class TestSoulEvolution(unittest.TestCase):
    """Test suite for SOUL memory ingestion, recall, and evolution."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.tmp_dir) / "test_soul_graph.kuzu"
        close_memory_db()
        self.db = get_memory_db(self.db_path)

    def tearDown(self):
        close_memory_db()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_recorder_captures_soul_decision(self):
        """Verifies TaskMemoryRecorder records SOUL decisions in memory."""
        rec = TaskMemoryRecorder(task_name="Test Task", goal="Verify SOUL logging")
        rec.record_soul_decision(
            decision_type="boolean",
            condition="Is 'Presentation' visible?",
            result=True,
            confidence=0.95,
            latency_ms=0.35,
            context_summary="Window: Canva | Elements: ['Presentation']",
        )

        self.assertEqual(len(rec.soul_decisions), 1)
        dec = rec.soul_decisions[0]
        self.assertEqual(dec["decision_type"], "boolean")
        self.assertEqual(dec["condition"], "Is 'Presentation' visible?")
        self.assertEqual(dec["result"], "True")
        self.assertAlmostEqual(dec["confidence"], 0.95)
        self.assertAlmostEqual(dec["latency_ms"], 0.35)

    def test_commit_soul_decisions_to_kuzudb(self):
        """Verifies SOUL decisions are committed to KùzuDB and linked to Task."""
        rec = TaskMemoryRecorder(task_name="SOUL Commit Task", goal="Test Kùzu DB linking")
        rec.record_soul_decision(
            decision_type="boolean",
            condition="Is error popup open?",
            result=False,
            confidence=0.92,
            latency_ms=0.45,
            context_summary="No error dialog found",
        )
        rec.record_soul_decision(
            decision_type="choice",
            condition="Select export format",
            result="PNG",
            confidence=0.98,
            latency_ms=0.55,
            context_summary="User asked for PNG image",
        )

        success = rec.commit_to_db(summary="Successfully executed SOUL task", success=True, custom_db_path=self.db_path)
        self.assertTrue(success)

        # Query via Cypher to verify nodes and relationships
        conn = get_memory_connection(self.db_path)
        res = conn.execute(
            """
            MATCH (t:Task {id: $task_id})-[:DECIDED]->(d:SoulDecision)
            RETURN d.decision_type, d.condition, d.result, d.confidence
            ORDER BY d.decision_type ASC
            """,
            {"task_id": rec.task_id},
        )

        rows = []
        while res.has_next():
            rows.append(res.get_next())

        self.assertEqual(len(rows), 2)
        # Verify boolean decision
        self.assertEqual(rows[0][0], "boolean")
        self.assertEqual(rows[0][1], "Is error popup open?")
        self.assertEqual(rows[0][2], "False")
        # Verify choice decision
        self.assertEqual(rows[1][0], "choice")
        self.assertEqual(rows[1][1], "Select export format")
        self.assertEqual(rows[1][2], "PNG")

    def test_recall_soul_decision_exact_match(self):
        """Verifies sub-2ms recall of past SOUL decisions from KùzuDB."""
        rec = TaskMemoryRecorder(task_name="Prior Decision Task")
        rec.record_soul_decision(
            decision_type="boolean",
            condition="Is 'Confirm Overwrite' dialog visible?",
            result=True,
            confidence=0.96,
            latency_ms=0.40,
            context_summary="Dialog: Confirm Overwrite detected",
        )
        rec.commit_to_db(summary="Saved prior decision", success=True, custom_db_path=self.db_path)

        # Sub-2ms recall query
        t0 = time.perf_counter()
        recalled = recall_soul_decision(
            condition="Is 'Confirm Overwrite' dialog visible?",
            custom_db_path=self.db_path,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertIsNotNone(recalled)
        self.assertEqual(recalled["source"], "prior_soul_decision")
        self.assertEqual(recalled["decision_type"], "boolean")
        self.assertEqual(recalled["result"], "True")
        self.assertAlmostEqual(recalled["confidence"], 0.96)
        self.assertLess(elapsed_ms, 5.0, f"Recall exceeded latency threshold: {elapsed_ms:.2f}ms")

    def test_decider_logs_to_active_recorder(self):
        """Verifies SoulDecider automatically pipes decisions to active memory recorder."""
        rec = start_memory_recording("Auto Logging Test", goal="Verify automatic decider logging")

        try:
            decider = SoulDecider()
            decider.decide_boolean("Is modal open?", context="Dialog: Save As", use_memory=False)
            decider.decide_choice("Pick tool", ["brush", "eraser"], context="Erase mistake")

            self.assertEqual(len(rec.soul_decisions), 2)
            self.assertEqual(rec.soul_decisions[0]["decision_type"], "boolean")
            self.assertEqual(rec.soul_decisions[1]["decision_type"], "choice")
        finally:
            finish_memory_recording(summary="Done test", success=True, async_commit=False)

    def test_decider_memory_recall_integration(self):
        """Verifies SoulDecider directly uses prior recalled memory when available."""
        # 1. Seed a decision into the DB
        rec = TaskMemoryRecorder(task_name="Seed Task")
        rec.record_soul_decision(
            decision_type="boolean",
            condition="Is dark mode enabled?",
            result=True,
            confidence=0.99,
            latency_ms=0.2,
            context_summary="Theme: dark",
        )
        rec.commit_to_db(summary="Seeded dark mode decision", success=True, custom_db_path=self.db_path)

        # 2. Invoke decide_boolean on decider with use_memory=True
        decider = SoulDecider()
        decision = decider.decide_boolean("Is dark mode enabled?", use_memory=True)

        self.assertEqual(decision.result, True)
        self.assertEqual(decision.model_name, "soul_recalled_memory")
        self.assertGreaterEqual(decision.confidence, 0.95)
        self.assertLess(decision.latency_ms, 15.0)

        # Warm lookup is sub-5ms
        decision_warm = decider.decide_boolean("Is dark mode enabled?", use_memory=True)
        self.assertEqual(decision_warm.result, True)
        self.assertLess(decision_warm.latency_ms, 5.0)

    def test_crystallize_soul_fastpath_structure(self):
        """Verifies crystallizing a SOUL fastpath creates a structured skill evolution."""
        res = crystallize_soul_fastpath(
            app_name="mock_app",
            trigger_condition="unexpected update popup",
            resolved_action="extra_hotkey(keys=['esc'])",
            confidence=0.95,
        )

        self.assertEqual(res["status"], "evolved")
        self.assertEqual(res["app_name"], "mock_app")
        self.assertIn("SOUL Fast-Path", res["workflow_summary"])
        self.assertTrue(len(res["skill_paths"]) > 0)


if __name__ == "__main__":
    unittest.main()
