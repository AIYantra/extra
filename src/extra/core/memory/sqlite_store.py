"""
SQLite FTS5 Storage Engine for Extra Memory Subsystem.
Provides zero-dependency, ultra-fast persistent task memory, BM25 text retrieval,
and app quirks caching when KùzuDB / FastEmbed are not installed.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Extra-Memory-SQLite")

_SQLITE_LOCK = threading.Lock()
_CONN_CACHE: Dict[str, sqlite3.Connection] = {}


def get_default_sqlite_path() -> Path:
    """Returns the default SQLite memory database path (~/.extra/memory/memory.sqlite3)."""
    base_dir = Path.home() / ".extra" / "memory"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / "memory.sqlite3"


def get_sqlite_connection(custom_path: Optional[Path] = None) -> sqlite3.Connection:
    """Returns a thread-safe SQLite connection with WAL mode and schema initialized."""
    target_path = custom_path or get_default_sqlite_path()
    path_str = str(target_path.resolve())

    with _SQLITE_LOCK:
        if path_str in _CONN_CACHE:
            try:
                _CONN_CACHE[path_str].execute("SELECT 1")
                return _CONN_CACHE[path_str]
            except Exception:
                pass

        target_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path_str, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        init_sqlite_schema(conn)
        _CONN_CACHE[path_str] = conn
        return conn


def close_sqlite_connections(custom_path: Optional[Path] = None) -> None:
    """Closes cached SQLite database connections."""
    with _SQLITE_LOCK:
        if custom_path:
            path_str = str(custom_path.resolve())
            if path_str in _CONN_CACHE:
                try:
                    _CONN_CACHE[path_str].close()
                except Exception:
                    pass
                del _CONN_CACHE[path_str]
        else:
            for p, conn in list(_CONN_CACHE.items()):
                try:
                    conn.close()
                except Exception:
                    pass
            _CONN_CACHE.clear()


def init_sqlite_schema(conn: sqlite3.Connection) -> None:
    """Initializes tables and FTS5 search indexes."""
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                goal TEXT NOT NULL,
                summary TEXT,
                timestamp REAL,
                duration_ms REAL,
                total_steps INTEGER,
                success INTEGER,
                apps TEXT,
                artifacts TEXT,
                steps TEXT,
                stalls TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS app_quirks (
                id TEXT PRIMARY KEY,
                app_name TEXT NOT NULL,
                issue TEXT NOT NULL,
                workaround TEXT NOT NULL,
                playbook TEXT
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS soul_decisions (
                id TEXT PRIMARY KEY,
                app_name TEXT,
                condition TEXT NOT NULL,
                decision_type TEXT,
                result TEXT,
                confidence REAL,
                context TEXT,
                timestamp REAL
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS app_sessions (
                service_name TEXT PRIMARY KEY,
                browser TEXT,
                profile_name TEXT,
                profile_path TEXT,
                last_verified INTEGER
            );
        """)

        # FTS5 Virtual Table for full-text search with BM25 ranking
        try:
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS tasks_fts USING fts5(
                    id UNINDEXED,
                    goal,
                    summary,
                    apps,
                    tokenize='porter unicode61'
                );
            """)
        except sqlite3.OperationalError as ex:
            logger.debug("FTS5 table initialization notice: %s", ex)


def sqlite_save_task(
    task_id: str,
    goal: str,
    summary: str,
    timestamp: float,
    duration_ms: float,
    total_steps: int,
    success: bool,
    apps: List[Dict[str, Any]],
    artifacts: List[Dict[str, Any]],
    steps: List[Dict[str, Any]],
    stalls: List[Dict[str, Any]],
    custom_path: Optional[Path] = None,
) -> None:
    """Persists a completed task and updates the FTS5 search index."""
    conn = get_sqlite_connection(custom_path)
    apps_str = json.dumps(apps, ensure_ascii=False)
    arts_str = json.dumps(artifacts, ensure_ascii=False)
    steps_str = json.dumps(steps, ensure_ascii=False)
    stalls_str = json.dumps(stalls, ensure_ascii=False)

    apps_text = " ".join(a.get("name", "") for a in apps)

    with _SQLITE_LOCK:
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO tasks (
                    id, goal, summary, timestamp, duration_ms, total_steps, success, apps, artifacts, steps, stalls
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    goal,
                    summary,
                    timestamp,
                    duration_ms,
                    total_steps,
                    1 if success else 0,
                    apps_str,
                    arts_str,
                    steps_str,
                    stalls_str,
                ),
            )
            try:
                # Remove existing FTS entry if updating
                conn.execute("DELETE FROM tasks_fts WHERE id = ?", (task_id,))
                conn.execute(
                    "INSERT INTO tasks_fts (id, goal, summary, apps) VALUES (?, ?, ?, ?)",
                    (task_id, goal, summary, apps_text),
                )
            except sqlite3.OperationalError:
                pass


def sqlite_save_quirk(
    app_name: str,
    issue: str,
    workaround: str,
    playbook: str,
    custom_path: Optional[Path] = None,
) -> None:
    """Saves or updates a known application quirk."""
    conn = get_sqlite_connection(custom_path)
    clean_app = app_name.strip().lower()
    quirk_id = f"quirk_{clean_app}_{abs(hash(issue)) % 1000000}"

    with _SQLITE_LOCK:
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO app_quirks (id, app_name, issue, workaround, playbook)
                VALUES (?, ?, ?, ?, ?)
                """,
                (quirk_id, clean_app, issue, workaround, playbook),
            )


def sqlite_save_soul_decision(
    decision_type: str,
    condition: str,
    result: str,
    confidence: float,
    context: str,
    app_name: Optional[str] = None,
    custom_path: Optional[Path] = None,
) -> None:
    """Saves a past SOUL decision for rapid reflexive lookup."""
    conn = get_sqlite_connection(custom_path)
    clean_app = app_name.strip().lower() if app_name else ""
    dec_id = f"dec_{int(time.time()*1000)}_{abs(hash(condition)) % 100000}"

    with _SQLITE_LOCK:
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO soul_decisions (
                    id, app_name, condition, decision_type, result, confidence, context, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (dec_id, clean_app, condition, decision_type, result, confidence, context, time.time()),
            )


def sqlite_save_app_session(
    service_name: str,
    browser: str,
    profile_name: str,
    profile_path: str,
    custom_path: Optional[Path] = None,
) -> None:
    """Saves an active app session."""
    conn = get_sqlite_connection(custom_path)
    clean_svc = service_name.strip().lower()

    with _SQLITE_LOCK:
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO app_sessions (
                    service_name, browser, profile_name, profile_path, last_verified
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (clean_svc, browser, profile_name, profile_path, int(time.time())),
            )


def sqlite_recall_memory(
    query: str,
    app_name: Optional[str] = None,
    top_k: int = 3,
    min_similarity: float = 0.40,
    custom_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Recalls past tasks using SQLite FTS5 BM25 search.
    Returns results conforming identically to the Kùzu memory schema.
    """
    conn = get_sqlite_connection(custom_path)
    tasks: List[Dict[str, Any]] = []
    matched_ids: List[str] = []

    # Clean query for FTS5 (strip punctuation that could cause syntax errors)
    clean_query = "".join(c if c.isalnum() or c.isspace() else " " for c in query).strip()
    words = [w for w in clean_query.split() if len(w) > 1]

    with _SQLITE_LOCK:
        if words:
            fts_expression = " OR ".join(f'"{w}"*' for w in words)
            try:
                cur = conn.execute(
                    """
                    SELECT t.id, t.goal, t.summary, t.timestamp, t.duration_ms, t.total_steps, t.success,
                           t.apps, t.artifacts, t.steps, bm25(tasks_fts) AS rank
                    FROM tasks_fts f
                    JOIN tasks t ON f.id = t.id
                    WHERE tasks_fts MATCH ?
                    ORDER BY rank ASC
                    LIMIT ?
                    """,
                    (fts_expression, top_k * 2),
                )
                for row in cur.fetchall():
                    t_id, goal, summary, ts, dur, steps_cnt, succ, apps_json, arts_json, steps_json, rank = row
                    
                    # App filter if requested
                    apps_list = json.loads(apps_json) if apps_json else []
                    if app_name:
                        target = app_name.strip().lower()
                        if not any(target in a.get("name", "").lower() for a in apps_list):
                            continue

                    arts_list = json.loads(arts_json) if arts_json else []
                    steps_list = json.loads(steps_json) if steps_json else []

                    # Convert BM25 rank to pseudo-similarity [0.4, 0.99]
                    norm_sim = min(0.99, max(0.40, round(1.0 / (1.0 + abs(rank) * 0.1), 3)))
                    if norm_sim >= min_similarity:
                        tasks.append({
                            "task_id": t_id,
                            "goal": goal,
                            "summary": summary,
                            "timestamp": ts,
                            "duration_ms": dur,
                            "total_steps": steps_cnt,
                            "success": bool(succ),
                            "similarity": norm_sim,
                            "apps": apps_list,
                            "artifacts": arts_list,
                            "key_steps": steps_list[:5],
                        })
                        matched_ids.append(t_id)
            except sqlite3.OperationalError:
                pass

        # Fallback to LIKE if FTS returned nothing or query has no alnum
        if not tasks:
            like_pat = f"%{query.strip()}%"
            cur = conn.execute(
                """
                SELECT id, goal, summary, timestamp, duration_ms, total_steps, success, apps, artifacts, steps
                FROM tasks
                WHERE goal LIKE ? OR summary LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (like_pat, like_pat, top_k),
            )
            for row in cur.fetchall():
                t_id, goal, summary, ts, dur, steps_cnt, succ, apps_json, arts_json, steps_json = row
                apps_list = json.loads(apps_json) if apps_json else []
                if app_name:
                    target = app_name.strip().lower()
                    if not any(target in a.get("name", "").lower() for a in apps_list):
                        continue

                tasks.append({
                    "task_id": t_id,
                    "goal": goal,
                    "summary": summary,
                    "timestamp": ts,
                    "duration_ms": dur,
                    "total_steps": steps_cnt,
                    "success": bool(succ),
                    "similarity": 0.75,
                    "apps": apps_list,
                    "artifacts": json.loads(arts_json) if arts_json else [],
                    "key_steps": (json.loads(steps_json) if steps_json else [])[:5],
                })

        # Fetch relevant app quirks
        app_quirks: List[Dict[str, Any]] = []
        if app_name:
            cur_q = conn.execute(
                "SELECT issue, workaround, playbook FROM app_quirks WHERE app_name = ? LIMIT 3",
                (app_name.strip().lower(),),
            )
            for q in cur_q.fetchall():
                app_quirks.append({
                    "issue": q[0],
                    "workaround": q[1],
                    "playbook": q[2],
                })

    tasks = tasks[:top_k]
    return {
        "query": query,
        "app_name": app_name,
        "tasks_found": len(tasks),
        "tasks": tasks,
        "quirks": app_quirks,
        "backend": "sqlite_fts5",
    }


def sqlite_recall_soul_decision(
    condition: str,
    app_name: Optional[str] = None,
    custom_path: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """Recalls past SOUL decisions from SQLite."""
    conn = get_sqlite_connection(custom_path)
    clean_cond = condition.strip().lower()
    clean_app = app_name.strip().lower() if app_name else ""

    with _SQLITE_LOCK:
        if clean_app:
            cur = conn.execute(
                """
                SELECT decision_type, result, confidence, context
                FROM soul_decisions
                WHERE app_name = ? AND lower(condition) = ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (clean_app, clean_cond),
            )
            row = cur.fetchone()
            if row:
                return {
                    "source": "prior_soul_decision",
                    "decision_type": row[0],
                    "result": row[1],
                    "confidence": float(row[2]),
                    "context": row[3],
                }

        cur = conn.execute(
            """
            SELECT decision_type, result, confidence, context
            FROM soul_decisions
            WHERE lower(condition) = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (clean_cond,),
        )
        row = cur.fetchone()
        if row:
            return {
                "source": "prior_soul_decision",
                "decision_type": row[0],
                "result": row[1],
                "confidence": float(row[2]),
                "context": row[3],
            }

    return None


def sqlite_recall_app_session(
    service_name: str,
    custom_path: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """Recalls past browser session from SQLite."""
    conn = get_sqlite_connection(custom_path)
    clean_svc = service_name.strip().lower()

    with _SQLITE_LOCK:
        cur = conn.execute(
            """
            SELECT service_name, browser, profile_name, profile_path, last_verified
            FROM app_sessions
            WHERE service_name = ?
            LIMIT 1
            """,
            (clean_svc,),
        )
        row = cur.fetchone()
        if row:
            return {
                "service_name": row[0],
                "browser": row[1],
                "profile_name": row[2],
                "profile_path": row[3],
                "last_verified": int(row[4]),
            }

    return None
