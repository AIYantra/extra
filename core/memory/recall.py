"""
Memory Recall and Hybrid Graph Retrieval Engine for Extra.
Searches past tasks via vector similarity and Cypher relationship traversal.
"""

from __future__ import annotations

import datetime
import json
import logging
from typing import Any, Dict, List, Optional

from extra.core.memory.db import close_memory_db, get_memory_connection
from extra.core.memory.embeddings import cosine_similarity, get_embedding

logger = logging.getLogger("Extra-Memory-Recall")


def recall_memory(
    query: str,
    app_name: Optional[str] = None,
    top_k: int = 3,
    min_similarity: float = 0.40,
    custom_db_path: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Recalls past task memories, successful workflows, artifacts, and known quirks.
    Performs hybrid vector similarity on task goals + Cypher graph traversal.
    """
    try:
        conn = get_memory_connection(custom_db_path)
        query_vec = get_embedding(query)

        # 1. Retrieve candidate tasks (optionally filtered by app)
        if app_name:
            cypher = """
                MATCH (t:Task)-[:TARGETED]->(a:App)
                WHERE lower(a.name) = lower($app_name)
                RETURN t.id, t.goal, t.summary, t.timestamp, t.duration_ms, t.total_steps, t.success, t.embedding
            """
            params = {"app_name": app_name.strip()}
        else:
            cypher = """
                MATCH (t:Task)
                RETURN t.id, t.goal, t.summary, t.timestamp, t.duration_ms, t.total_steps, t.success, t.embedding
            """
            params = {}

        res = conn.execute(cypher, params)
        candidates = []
        while res.has_next():
            row = res.get_next()
            t_id, goal, summary, ts, dur, steps, success, emb = row
            sim = cosine_similarity(query_vec, emb)
            if sim >= min_similarity:
                candidates.append({
                    "task_id": t_id,
                    "goal": goal,
                    "summary": summary,
                    "timestamp": ts,
                    "duration_ms": dur,
                    "total_steps": steps,
                    "success": success,
                    "similarity": round(sim, 3),
                })

        # Sort by similarity descending
        candidates.sort(key=lambda x: x["similarity"], reverse=True)
        top_tasks = candidates[:top_k]

        enriched_results = []
        app_quirks = []

        # 2. Enrich top tasks with relationships
        for task in top_tasks:
            t_id = task["task_id"]

            # Query Apps
            apps_res = conn.execute(
                "MATCH (t:Task {id: $id})-[:TARGETED]->(a:App) RETURN a.name, a.ui_type",
                {"id": t_id},
            )
            apps = []
            while apps_res.has_next():
                r = apps_res.get_next()
                apps.append({"name": r[0], "ui_type": r[1]})

            # Query Artifacts
            art_res = conn.execute(
                "MATCH (t:Task {id: $id})-[:PRODUCED]->(art:Artifact) RETURN art.file_path, art.mime_type, art.size_bytes",
                {"id": t_id},
            )
            artifacts = []
            while art_res.has_next():
                r = art_res.get_next()
                artifacts.append({"file_path": r[0], "mime_type": r[1], "size_bytes": r[2]})

            # Query Key Steps
            steps_res = conn.execute(
                """
                MATCH (t:Task {id: $id})-[:EXECUTED]->(s:ActionStep)
                RETURN s.step_num, s.tool_name, s.parameters
                ORDER BY s.step_num ASC
                LIMIT 20
                """,
                {"id": t_id},
            )
            key_steps = []
            while steps_res.has_next():
                r = steps_res.get_next()
                param_preview = r[2]
                try:
                    p_obj = json.loads(param_preview)
                    # summarize
                    param_preview = {k: v for k, v in p_obj.items() if k in ["app_name", "window_title", "text", "keys", "delta", "action", "url"]}
                except:
                    pass
                key_steps.append({
                    "step": r[0],
                    "tool": r[1],
                    "params": param_preview,
                })

            human_time = datetime.datetime.fromtimestamp(task["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")

            # Query Soul Decisions
            try:
                dec_res = conn.execute(
                    """
                    MATCH (t:Task {id: $id})-[:DECIDED]->(d:SoulDecision)
                    RETURN d.decision_type, d.condition, d.result, d.confidence
                    LIMIT 10
                    """,
                    {"id": t_id},
                )
                soul_decisions = []
                while dec_res.has_next():
                    dr = dec_res.get_next()
                    soul_decisions.append({
                        "decision_type": dr[0],
                        "condition": dr[1],
                        "result": dr[2],
                        "confidence": dr[3],
                    })
            except Exception:
                soul_decisions = []

            enriched_results.append({
                "task_id": t_id,
                "goal": task["goal"],
                "summary": task["summary"],
                "datetime": human_time,
                "similarity": task["similarity"],
                "success": task["success"],
                "apps": apps,
                "artifacts": artifacts,
                "key_steps": key_steps,
                "soul_decisions": soul_decisions,
            })

        # 3. Query Quirks / Workarounds for relevant apps
        queried_apps = [app_name] if app_name else [a["name"] for t in enriched_results for a in t.get("apps", [])]
        for app in set(queried_apps):
            if not app:
                continue
            q_res = conn.execute(
                """
                MATCH (a:App)-[:EXHIBITS]->(q:AppQuirk)
                WHERE lower(a.name) = lower($app)
                RETURN q.issue, q.workaround, q.playbook
                """,
                {"app": app.strip()},
            )
            while q_res.has_next():
                r = q_res.get_next()
                app_quirks.append({
                    "app": app,
                    "issue": r[0],
                    "workaround": r[1],
                    "playbook": r[2],
                })

        return {
            "query": query,
            "total_matches": len(enriched_results),
            "memories": enriched_results,
            "known_app_quirks": app_quirks,
        }

    except Exception as ex:
        logger.error("Memory recall error: %s", ex, exc_info=True)
        return {
            "query": query,
            "total_matches": 0,
            "memories": [],
            "error": str(ex),
        }


_SOUL_DECISION_CACHE: Dict[str, Optional[Dict[str, Any]]] = {}


def clear_soul_decision_cache() -> None:
    _SOUL_DECISION_CACHE.clear()


def recall_soul_decision(
    condition: str,
    app_name: Optional[str] = None,
    custom_db_path: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    """
    Sub-2ms reflexive memory lookup for past SOUL decisions and app quirks.
    Returns matching prior decision dict or None if no match found.
    """
    cond_clean = condition.strip().lower()
    cache_key = f"{app_name or ''}:{cond_clean}"
    if custom_db_path is None and cache_key in _SOUL_DECISION_CACHE:
        return _SOUL_DECISION_CACHE[cache_key]

    try:
        conn = get_memory_connection(custom_db_path, max_retries=0)

        # 1. Match against past SoulDecisions
        res = conn.execute(
            """
            MATCH (d:SoulDecision)
            WHERE lower(d.condition) = lower($cond)
            RETURN d.decision_type, d.result, d.confidence, d.context
            LIMIT 1
            """,
            {"cond": cond_clean},
        )
        if res.has_next():
            row = res.get_next()
            ret = {
                "source": "prior_soul_decision",
                "decision_type": row[0],
                "result": row[1],
                "confidence": float(row[2]),
                "context": row[3],
            }
            if custom_db_path is None:
                _SOUL_DECISION_CACHE[cache_key] = ret
            return ret

        # 2. Match against AppQuirk if app_name given
        if app_name:
            q_res = conn.execute(
                """
                MATCH (a:App)-[:EXHIBITS]->(q:AppQuirk)
                WHERE lower(a.name) = lower($app_name) AND (lower(q.issue) CONTAINS lower($cond) OR lower(q.playbook) CONTAINS lower($cond))
                RETURN q.issue, q.workaround, q.playbook
                LIMIT 1
                """,
                {"app_name": app_name.strip(), "cond": cond_clean},
            )
            if q_res.has_next():
                q_row = q_res.get_next()
                ret = {
                    "source": "app_quirk_memory",
                    "decision_type": "boolean",
                    "result": q_row[1],
                    "confidence": 0.92,
                    "context": f"Issue: {q_row[0]} | Workaround: {q_row[1]}",
                }
                if custom_db_path is None:
                    _SOUL_DECISION_CACHE[cache_key] = ret
                return ret
        if custom_db_path is None:
            _SOUL_DECISION_CACHE[cache_key] = None
    except Exception as ex:
        logger.debug("recall_soul_decision lookup skipped: %s", ex)
        if custom_db_path is None:
            _SOUL_DECISION_CACHE[cache_key] = None
    return None

