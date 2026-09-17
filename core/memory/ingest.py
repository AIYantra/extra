"""
Task Memory Ingestion Pipeline for Extra.
Captures tool execution traces, stalls, and artifacts, asynchronously persisting them into KùzuDB.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from extra.core.memory.db import get_memory_connection
from extra.core.memory.embeddings import get_embedding

logger = logging.getLogger("Extra-Memory-Ingest")

_ACTIVE_RECORDER: Optional[TaskMemoryRecorder] = None
_RECORDER_LOCK = threading.Lock()


class TaskMemoryRecorder:
    """Records real-time execution events for an active task session."""

    def __init__(self, task_name: str, goal: Optional[str] = None):
        self.task_id = f"task_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        self.task_name = task_name
        self.goal = goal or task_name
        self.start_time = time.time()
        self.steps: List[Dict[str, Any]] = []
        self.apps: Dict[str, Dict[str, Any]] = {}
        self.artifacts: List[Dict[str, Any]] = []
        self.stalls: List[Dict[str, Any]] = []
        self.quirks: List[Dict[str, Any]] = []
        self.completed = False
        self._lock = threading.Lock()

    def record_step(self, tool_name: str, parameters: Dict[str, Any], duration_ms: float = 0.0) -> None:
        with self._lock:
            step_num = len(self.steps) + 1
            # Sanitize parameters for clean JSON storage
            clean_params = {}
            for k, v in parameters.items():
                if isinstance(v, (str, int, float, bool, list, dict)) or v is None:
                    clean_params[k] = v
                else:
                    clean_params[k] = str(v)

            self.steps.append({
                "step_num": step_num,
                "tool_name": tool_name,
                "parameters": json.dumps(clean_params, ensure_ascii=False),
                "duration_ms": float(duration_ms),
            })

    def record_app(self, app_name: str, exe_path: Optional[str] = None, ui_type: Optional[str] = None) -> None:
        with self._lock:
            key = app_name.strip().lower()
            if key not in self.apps:
                self.apps[key] = {
                    "name": app_name.strip(),
                    "exe_path": exe_path or "",
                    "ui_type": ui_type or "standard",
                }

    def record_artifact(self, file_path: str, mime_type: Optional[str] = None) -> None:
        with self._lock:
            p = Path(file_path)
            size = p.stat().st_size if p.exists() else 0
            self.artifacts.append({
                "file_path": str(file_path),
                "mime_type": mime_type or (p.suffix[1:] if p.suffix else "unknown"),
                "size_bytes": size,
            })

    def record_stall(self, strike_count: int, trigger_action: str, resolution: Optional[str] = None) -> None:
        with self._lock:
            self.stalls.append({
                "strike_count": int(strike_count),
                "trigger_action": str(trigger_action),
                "resolution": resolution or "",
            })

    def record_quirk(self, app_name: str, issue: str, workaround: str, playbook: str) -> None:
        with self._lock:
            self.quirks.append({
                "app_name": app_name,
                "issue": issue,
                "workaround": workaround,
                "playbook": playbook,
            })

    def commit_to_db(self, summary: str, success: bool = True, custom_db_path: Optional[Path] = None) -> bool:
        """Commits the full task trajectory to KùzuDB."""
        try:
            conn = get_memory_connection(custom_db_path)
            duration_ms = (time.time() - self.start_time) * 1000.0

            # Compute semantic embedding on full intent + outcome
            text_to_embed = f"{self.task_name}: {self.goal}\nSummary: {summary}"
            embedding_vec = get_embedding(text_to_embed)

            # 1. Insert Task Node
            conn.execute(
                """
                CREATE (t:Task {
                    id: $id,
                    goal: $goal,
                    summary: $summary,
                    timestamp: $timestamp,
                    duration_ms: $duration_ms,
                    total_steps: $total_steps,
                    success: $success,
                    embedding: $embedding
                })
                """,
                {
                    "id": self.task_id,
                    "goal": self.goal,
                    "summary": summary,
                    "timestamp": self.start_time,
                    "duration_ms": duration_ms,
                    "total_steps": len(self.steps),
                    "success": success,
                    "embedding": embedding_vec,
                },
            )

            # 2. Insert and link Apps
            for app_info in self.apps.values():
                conn.execute(
                    """
                    MERGE (a:App {name: $name})
                    ON CREATE SET a.exe_path = $exe_path, a.ui_type = $ui_type
                    """,
                    {
                        "name": app_info["name"],
                        "exe_path": app_info["exe_path"],
                        "ui_type": app_info["ui_type"],
                    },
                )
                conn.execute(
                    """
                    MATCH (t:Task {id: $task_id}), (a:App {name: $app_name})
                    CREATE (t)-[:TARGETED]->(a)
                    """,
                    {"task_id": self.task_id, "app_name": app_info["name"]},
                )

            # 3. Insert and link ActionSteps (cap to last 50 steps to keep graph compact)
            for step in self.steps[-50:]:
                step_id = f"{self.task_id}_s{step['step_num']}"
                conn.execute(
                    """
                    CREATE (s:ActionStep {
                        id: $id,
                        step_num: $step_num,
                        tool_name: $tool_name,
                        parameters: $parameters,
                        duration_ms: $duration_ms
                    })
                    """,
                    {
                        "id": step_id,
                        "step_num": step["step_num"],
                        "tool_name": step["tool_name"],
                        "parameters": step["parameters"],
                        "duration_ms": step["duration_ms"],
                    },
                )
                conn.execute(
                    """
                    MATCH (t:Task {id: $task_id}), (s:ActionStep {id: $step_id})
                    CREATE (t)-[:EXECUTED]->(s)
                    """,
                    {"task_id": self.task_id, "step_id": step_id},
                )

            # 4. Insert and link Artifacts
            for idx, art in enumerate(self.artifacts):
                art_id = f"{self.task_id}_art{idx}"
                conn.execute(
                    """
                    CREATE (r:Artifact {
                        id: $id,
                        file_path: $file_path,
                        mime_type: $mime_type,
                        size_bytes: $size_bytes
                    })
                    """,
                    {
                        "id": art_id,
                        "file_path": art["file_path"],
                        "mime_type": art["mime_type"],
                        "size_bytes": art["size_bytes"],
                    },
                )
                conn.execute(
                    """
                    MATCH (t:Task {id: $task_id}), (r:Artifact {id: $art_id})
                    CREATE (t)-[:PRODUCED]->(r)
                    """,
                    {"task_id": self.task_id, "art_id": art_id},
                )

            # 5. Insert and link Stalls
            for idx, stall in enumerate(self.stalls):
                stall_id = f"{self.task_id}_stall{idx}"
                conn.execute(
                    """
                    CREATE (e:StallEvent {
                        id: $id,
                        strike_count: $strike_count,
                        trigger_action: $trigger_action,
                        resolution: $resolution
                    })
                    """,
                    {
                        "id": stall_id,
                        "strike_count": stall["strike_count"],
                        "trigger_action": stall["trigger_action"],
                        "resolution": stall["resolution"],
                    },
                )
                conn.execute(
                    """
                    MATCH (t:Task {id: $task_id}), (e:StallEvent {id: $stall_id})
                    CREATE (t)-[:ENCOUNTERED]->(e)
                    """,
                    {"task_id": self.task_id, "stall_id": stall_id},
                )

            # 6. Insert and link Quirks
            for idx, quirk in enumerate(self.quirks):
                quirk_id = f"quirk_{quirk['app_name']}_{int(time.time())}_{idx}"
                conn.execute(
                    """
                    CREATE (q:AppQuirk {
                        id: $id,
                        issue: $issue,
                        workaround: $workaround,
                        playbook: $playbook
                    })
                    """,
                    {
                        "id": quirk_id,
                        "issue": quirk["issue"],
                        "workaround": quirk["workaround"],
                        "playbook": quirk["playbook"],
                    },
                )
                conn.execute(
                    """
                    MATCH (a:App {name: $app_name}), (q:AppQuirk {id: $quirk_id})
                    CREATE (a)-[:EXHIBITS]->(q)
                    """,
                    {"app_name": quirk["app_name"], "quirk_id": quirk_id},
                )

            logger.info("Successfully persisted task '%s' (%s) to KùzuDB memory.", self.task_name, self.task_id)
            return True
        except Exception as ex:
            logger.error("Failed to commit task memory to KùzuDB: %s", ex, exc_info=True)
            return False


def start_memory_recording(task_name: str, goal: Optional[str] = None) -> TaskMemoryRecorder:
    """Initializes and activates a new task memory recorder."""
    global _ACTIVE_RECORDER
    with _RECORDER_LOCK:
        _ACTIVE_RECORDER = TaskMemoryRecorder(task_name, goal)
        return _ACTIVE_RECORDER


def get_active_recorder() -> Optional[TaskMemoryRecorder]:
    """Returns the currently active recorder, if any."""
    global _ACTIVE_RECORDER
    with _RECORDER_LOCK:
        return _ACTIVE_RECORDER


def finish_memory_recording(summary: str, success: bool = True, async_commit: bool = True) -> Optional[str]:
    """Finalizes active task recording and initiates database commit."""
    global _ACTIVE_RECORDER
    recorder = None
    with _RECORDER_LOCK:
        if _ACTIVE_RECORDER and not _ACTIVE_RECORDER.completed:
            _ACTIVE_RECORDER.completed = True
            recorder = _ACTIVE_RECORDER
            _ACTIVE_RECORDER = None

    if not recorder:
        return None

    if async_commit:
        t = threading.Thread(
            target=recorder.commit_to_db,
            args=(summary, success),
            daemon=True,
            name=f"ExtraMemoryCommit-{recorder.task_id}",
        )
        t.start()
    else:
        recorder.commit_to_db(summary, success)

    return recorder.task_id


def record_action_step(tool_name: str, parameters: Dict[str, Any], duration_ms: float = 0.0) -> None:
    """Records an executed action step into the active recorder, if running."""
    rec = get_active_recorder()
    if rec and not rec.completed:
        try:
            rec.record_step(tool_name, parameters, duration_ms)
        except Exception as ex:
            logger.debug("Could not record action step: %s", ex)


def record_action_app(app_name: str, exe_path: Optional[str] = None, ui_type: Optional[str] = None) -> None:
    """Records a targeted desktop application into the active recorder, if running; otherwise persists directly."""
    rec = get_active_recorder()
    if rec and not rec.completed:
        try:
            rec.record_app(app_name, exe_path, ui_type)
            return
        except Exception as ex:
            logger.debug("Could not record app: %s", ex)

    # Standalone direct ingestion
    try:
        conn = get_memory_connection()
        clean_app = app_name.strip().lower()
        conn.execute(
            """
            MERGE (a:App {name: $name})
            ON CREATE SET a.exe_path = $exe_path, a.ui_type = $ui_type
            """,
            {
                "name": clean_app,
                "exe_path": exe_path or "",
                "ui_type": ui_type or "standard",
            },
        )
    except Exception as ex:
        logger.debug("Could not persist standalone app to KùzuDB: %s", ex)


def record_action_artifact(file_path: str, mime_type: Optional[str] = None) -> None:
    """Records a created file artifact into the active recorder, if running."""
    rec = get_active_recorder()
    if rec and not rec.completed:
        try:
            rec.record_artifact(file_path, mime_type)
        except Exception as ex:
            logger.debug("Could not record artifact: %s", ex)


def record_action_stall(strike_count: int, trigger_action: str, resolution: Optional[str] = None) -> None:
    """Records a StallBreaker strike event into the active recorder, if running."""
    rec = get_active_recorder()
    if rec and not rec.completed:
        try:
            rec.record_stall(strike_count, trigger_action, resolution)
        except Exception as ex:
            logger.debug("Could not record stall: %s", ex)


def record_action_quirk(app_name: str, issue: str, workaround: str, playbook: str) -> None:
    """Records an app quirk or known workaround into the active recorder, if running; otherwise persists directly."""
    rec = get_active_recorder()
    if rec and not rec.completed:
        try:
            rec.record_quirk(app_name, issue, workaround, playbook)
            return
        except Exception as ex:
            logger.debug("Could not record quirk: %s", ex)

    # Standalone direct ingestion
    try:
        conn = get_memory_connection()
        clean_app = app_name.strip().lower()
        conn.execute(
            """
            MERGE (a:App {name: $name})
            ON CREATE SET a.exe_path = '', a.ui_type = 'standard'
            """,
            {"name": clean_app},
        )
        quirk_id = f"quirk_{clean_app}_{int(time.time() * 1000)}"
        conn.execute(
            """
            CREATE (q:AppQuirk {
                id: $id,
                issue: $issue,
                workaround: $workaround,
                playbook: $playbook
            })
            """,
            {
                "id": quirk_id,
                "issue": issue,
                "workaround": workaround,
                "playbook": playbook,
            },
        )
        conn.execute(
            """
            MATCH (a:App {name: $app_name}), (q:AppQuirk {id: $quirk_id})
            CREATE (a)-[:EXHIBITS]->(q)
            """,
            {"app_name": clean_app, "quirk_id": quirk_id},
        )
    except Exception as ex:
        logger.debug("Could not persist standalone quirk to KùzuDB: %s", ex)

