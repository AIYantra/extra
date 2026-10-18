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

    def test_app_session_recording_and_instant_recall(self):
        """Verify record_app_session persists environmental profile and recall_app_session retrieves it."""
        from extra.core.memory.ingest import record_app_session
        from extra.core.memory.recall import recall_app_session, recall_memory, clear_app_session_cache

        clear_app_session_cache()

        # Ingest an environmental profile
        ok = record_app_session(
            service_name="meta_business_suite",
            browser="chrome",
            profile_name="Profile 3",
            profile_path="C:\\Users\\Test\\AppData\\Local\\Google\\Chrome\\User Data\\Profile 3",
            custom_db_path=self.db_path,
        )
        self.assertTrue(ok)

        # Recall directly via recall_app_session
        t0 = time.perf_counter()
        session = recall_app_session("meta_business_suite", custom_db_path=self.db_path)
        lookup_ms = (time.perf_counter() - t0) * 1000.0

        self.assertIsNotNone(session)
        self.assertEqual(session["browser"], "chrome")
        self.assertEqual(session["profile_name"], "Profile 3")
        self.assertIn("User Data", session["profile_path"])

        # Recall via recall_memory with app_name filter
        rec = recall_memory(
            query="post scheduled update to meta",
            app_name="meta_business_suite",
            custom_db_path=self.db_path,
        )
        self.assertIn("active_session", rec)
        self.assertEqual(rec["active_session"]["profile_name"], "Profile 3")

        # Update session (testing ON MATCH SET)
        ok_update = record_app_session(
            service_name="meta_business_suite",
            browser="chrome",
            profile_name="Profile 5",
            profile_path="C:\\Users\\Test\\AppData\\Local\\Google\\Chrome\\User Data\\Profile 5",
            custom_db_path=self.db_path,
        )
        self.assertTrue(ok_update)

        session_updated = recall_app_session("meta_business_suite", custom_db_path=self.db_path)
        self.assertEqual(session_updated["profile_name"], "Profile 5")

    def test_recall_soul_decision_app_scoping_and_length_validation(self):
        """Verify recall_soul_decision isolates by app and rejects short/empty conditions."""
        from extra.core.memory.recall import recall_soul_decision, clear_soul_decision_cache

        clear_soul_decision_cache()

        # Reject short conditions
        self.assertIsNone(recall_soul_decision("", custom_db_path=self.db_path))
        self.assertIsNone(recall_soul_decision("ab", custom_db_path=self.db_path))

        # Insert test quirk for App A directly into test DB
        conn = get_memory_connection(self.db_path)
        conn.execute("MERGE (a:App {name: 'canva'}) ON CREATE SET a.exe_path = '', a.ui_type = 'electron'")
        conn.execute("CREATE (q:AppQuirk {id: 'q_test_1', issue: 'template popup blocked', workaround: 'press esc', playbook: 'press esc'})")
        conn.execute("MATCH (a:App {name: 'canva'}), (q:AppQuirk {id: 'q_test_1'}) CREATE (a)-[:EXHIBITS]->(q)")

        # Query with matching app
        res_matching = recall_soul_decision("template popup blocked", app_name="canva", custom_db_path=self.db_path)
        self.assertIsNotNone(res_matching)
        self.assertEqual(res_matching["result"], "press esc")

        # Query with different app - should NOT return canva quirk
        clear_soul_decision_cache()
        res_different = recall_soul_decision("template popup blocked", app_name="blender", custom_db_path=self.db_path)
        self.assertIsNone(res_different)


if __name__ == "__main__":
    unittest.main()
