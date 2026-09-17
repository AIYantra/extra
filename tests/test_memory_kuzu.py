"""
Tests for Extra Memory Subsystem (KùzuDB + FastEmbed).
Validates episodic task recording, hybrid vector + Cypher graph traversal, and artifact recall.
"""

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from extra.core.memory.db import close_memory_db, get_memory_connection, get_memory_db
from extra.core.memory.embeddings import cosine_similarity, get_embedding
from extra.core.memory.ingest import TaskMemoryRecorder
from extra.core.memory.recall import recall_memory


class TestExtraMemory(unittest.TestCase):
    """Test suite for Extra local episodic memory and knowledge graph."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.tmp_dir) / "test_graph.kuzu"
        # Force get_memory_db to use temporary path
        close_memory_db()
        self.db = get_memory_db(self.db_path)

    def tearDown(self):
        close_memory_db()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_embeddings_generation_and_similarity(self):
        """Verify FastEmbed generates 384-dim normalized vectors with logical cosine similarities."""
        v1 = get_embedding("Create an Instagram launch poster in Canva")
        v2 = get_embedding("Design a Canva template for social media poster")
        v3 = get_embedding("Bake a sourdough bread in the kitchen oven")

        self.assertEqual(len(v1), 384)
        self.assertEqual(len(v2), 384)
        self.assertEqual(len(v3), 384)

        sim_related = cosine_similarity(v1, v2)
        sim_unrelated = cosine_similarity(v1, v3)

        self.assertGreater(sim_related, 0.70, f"Expected high similarity between related tasks, got {sim_related}")
        self.assertLess(sim_unrelated, 0.45, f"Expected low similarity between unrelated tasks, got {sim_unrelated}")

    def test_task_recording_and_graph_commit(self):
        """Verify TaskMemoryRecorder writes nodes and relationships into KùzuDB."""
        recorder = TaskMemoryRecorder(
            task_name="Canva Poster Task",
            goal="Create an Instagram launch poster of Extra in Canva"
        )
        recorder.record_app("Canva", exe_path="C:\\Users\\Test\\AppData\\Local\\Canva\\Canva.exe", ui_type="electron")
        recorder.record_app("Edge", exe_path="C:\\Program Files\\Edge\\msedge.exe", ui_type="native")

        recorder.record_step("extra_launch", {"app_name": "edge"}, duration_ms=45.0)
        recorder.record_step("extra_launch", {"app_name": "canva"}, duration_ms=80.0)
        recorder.record_step("extra_hotkey", {"keys": ["ctrl", "v"]}, duration_ms=15.0)

        recorder.record_artifact("C:\\Users\\Test\\.extra\\workspace\\extra_poster.png", mime_type="png")
        recorder.record_stall(strike_count=2, trigger_action="click(650, 450)", resolution="bypassed via clipboard paste")
        recorder.record_quirk(
            app_name="Canva",
            issue="WebGL canvas does not expose Win32 UIA controls",
            workaround="Generate PNG with PIL and paste via clipboard",
            playbook="powershell SetImage + extra_hotkey(['ctrl', 'v'])"
        )

        ok = recorder.commit_to_db(
            summary="Successfully pasted generated poster into Canva canvas",
            success=True,
            custom_db_path=self.db_path,
        )
        self.assertTrue(ok, "Commit to KùzuDB failed")

        # Verify via direct Cypher query
        conn = get_memory_connection(self.db_path)
        res = conn.execute("MATCH (t:Task)-[:TARGETED]->(a:App) RETURN t.goal, a.name")
        targeted_apps = set()
        while res.has_next():
            row = res.get_next()
            targeted_apps.add(row[1])

        self.assertIn("Canva", targeted_apps)
        self.assertIn("Edge", targeted_apps)

    def test_memory_recall_hybrid_engine(self):
        """Verify recall_memory successfully retrieves past tasks, artifacts, and known quirks."""
        # 1. Ingest a sample task
        recorder = TaskMemoryRecorder(
            task_name="Canva Launch Poster",
            goal="open edge analyze extra site and create launch poster in canva for instagram"
        )
        recorder.record_app("Canva", ui_type="electron")
        recorder.record_artifact("C:\\Users\\AdLoa\\.extra\\workspace\\extra_instagram_launch_poster.png", mime_type="png")
        recorder.record_quirk(
            app_name="Canva",
            issue="Chromium webview canvas unclickable via UIA",
            workaround="Use PowerShell SetImage and press Ctrl+V",
            playbook="PIL ImageDraw -> Clipboard -> Focus -> Ctrl+V"
        )
        recorder.commit_to_db(
            summary="Designed 1080x1440 graphic in PIL, loaded to clipboard, and pasted into Canva",
            success=True,
            custom_db_path=self.db_path,
        )

        # 2. Query with natural language
        recalled = recall_memory(
            query="remember the task of creating canva template a week ago",
            top_k=2,
            custom_db_path=self.db_path,
        )

        self.assertGreaterEqual(recalled["total_matches"], 1)
        top_match = recalled["memories"][0]
        self.assertIn("canva", top_match["goal"].lower())
        self.assertTrue(len(top_match["artifacts"]) >= 1)
        self.assertEqual(
            top_match["artifacts"][0]["file_path"],
            "C:\\Users\\AdLoa\\.extra\\workspace\\extra_instagram_launch_poster.png"
        )

        # Verify quirks retrieved
        quirks = recalled.get("known_app_quirks", [])
        self.assertTrue(len(quirks) >= 1)
        self.assertIn("PowerShell SetImage", quirks[0]["workaround"])


if __name__ == "__main__":
    unittest.main()
