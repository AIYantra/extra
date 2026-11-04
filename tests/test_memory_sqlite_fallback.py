"""
Unit Tests for SQLite FTS5 Zero-Dependency Memory Fallback Engine.
Verifies that Extra's memory, recall, quirks, and sessions operate 100% reliably
in the <6.3 MB Core Tier without requiring KùzuDB or FastEmbed.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from extra.core.memory.embeddings import get_embedding
from extra.core.memory.ingest import (
    TaskMemoryRecorder,
    record_action_quirk,
    record_app_session,
)
from extra.core.memory.recall import (
    recall_app_session,
    recall_memory,
    recall_soul_decision,
)
from extra.core.memory.sqlite_store import (
    close_sqlite_connections,
    get_sqlite_connection,
    sqlite_recall_app_session,
    sqlite_recall_memory,
    sqlite_recall_soul_decision,
    sqlite_save_app_session,
    sqlite_save_quirk,
    sqlite_save_soul_decision,
    sqlite_save_task,
)


@pytest.fixture
def temp_sqlite_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_memory.sqlite3"
        try:
            yield db_path
        finally:
            close_sqlite_connections(db_path)


def test_sqlite_save_and_recall_task(temp_sqlite_db):
    """Verifies saving and retrieving tasks via SQLite FTS5 BM25 search."""
    task_id = "task_test_001"
    goal = "Create Instagram marketing poster in Canva"
    summary = "Opened Canva, selected template, added brand logo, exported PNG"
    apps = [{"name": "Canva", "ui_type": "electron"}]
    artifacts = [{"file_path": "C:/tmp/poster.png", "mime_type": "png", "size_bytes": 1024}]
    steps = [{"step_num": 1, "tool_name": "extra_launch", "parameters": '{"app": "canva"}'}]
    stalls = []

    sqlite_save_task(
        task_id=task_id,
        goal=goal,
        summary=summary,
        timestamp=time.time(),
        duration_ms=1250.0,
        total_steps=1,
        success=True,
        apps=apps,
        artifacts=artifacts,
        steps=steps,
        stalls=stalls,
        custom_path=temp_sqlite_db,
    )

    # Search with FTS query
    res = sqlite_recall_memory("Canva poster", app_name="Canva", custom_path=temp_sqlite_db)
    assert res["tasks_found"] >= 1
    top_task = res["tasks"][0]
    assert top_task["task_id"] == task_id
    assert "Canva" in top_task["goal"]
    assert len(top_task["artifacts"]) == 1
    assert res["backend"] == "sqlite_fts5"


def test_sqlite_save_and_recall_quirk(temp_sqlite_db):
    """Verifies app quirks storage and recall."""
    sqlite_save_quirk(
        app_name="LibreOffice Calc",
        issue="Context menu dismisses on screenshot",
        workaround="Use Alt+/ menu search or Shift+F11 hotkey",
        playbook="Send Shift+F11 directly to add tab without context menu",
        custom_path=temp_sqlite_db,
    )

    res = sqlite_recall_memory("export", app_name="LibreOffice Calc", custom_path=temp_sqlite_db)
    assert len(res["quirks"]) >= 1
    q = res["quirks"][0]
    assert "Shift+F11" in q["workaround"]


def test_sqlite_soul_decision_and_app_session(temp_sqlite_db):
    """Verifies reflexive SOUL decisions and browser sessions in SQLite."""
    # 1. SOUL decision
    sqlite_save_soul_decision(
        decision_type="boolean",
        condition="cookie_consent_banner",
        result="dismissed",
        confidence=0.95,
        context="Clicked Accept All Cookies via UIA button",
        app_name="Chrome",
        custom_path=temp_sqlite_db,
    )

    dec = sqlite_recall_soul_decision("cookie_consent_banner", app_name="Chrome", custom_path=temp_sqlite_db)
    assert dec is not None
    assert dec["result"] == "dismissed"
    assert dec["confidence"] == 0.95

    # 2. App Session
    sqlite_save_app_session(
        service_name="canva_pro",
        browser="chrome",
        profile_name="Profile 1",
        profile_path="/tmp/profile",
        custom_path=temp_sqlite_db,
    )

    sess = sqlite_recall_app_session("canva_pro", custom_path=temp_sqlite_db)
    assert sess is not None
    assert sess["browser"] == "chrome"
    assert sess["profile_name"] == "Profile 1"


def test_mocked_core_tier_without_kuzu(temp_sqlite_db):
    """Simulates a machine with Kùzu not installed, verifying end-to-end memory pipeline."""
    with patch("extra.core.memory.recall.has_kuzu", return_value=False), \
         patch("extra.core.memory.ingest.has_kuzu", return_value=False), \
         patch("extra.core.memory.sqlite_store.get_default_sqlite_path", return_value=temp_sqlite_db):

        # 1. Record task
        rec = TaskMemoryRecorder("financial_model_task", goal="Build financial model in Excel")
        rec.record_app("Excel", "excel.exe", "win32")
        rec.record_step("extra_type", {"text": "=SUM(A1:A10)"}, 5.0)
        rec.commit_to_db(summary="Successfully computed revenue formulas in Excel", success=True, custom_db_path=temp_sqlite_db)

        # 2. Recall task
        result = recall_memory("Excel financial formulas", app_name="Excel", custom_db_path=temp_sqlite_db)
        assert result["tasks_found"] >= 1
        assert "Excel" in result["tasks"][0]["goal"]
        assert result["backend"] == "sqlite_fts5"


def test_fallback_embeddings_without_fastembed():
    """Verifies that get_embedding produces valid 384-float vectors even when fastembed is absent."""
    with patch("extra.core.memory.embeddings.get_embedding_model", return_value=None):
        vec = get_embedding("Hello world desktop automation")
        assert len(vec) == 384
        assert isinstance(vec[0], float)
        # Verify unit normalization sum(x^2) ~ 1.0
        norm = sum(x * x for x in vec)
        assert pytest.approx(norm, 0.05) == 1.0
