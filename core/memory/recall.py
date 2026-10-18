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
            clean_app = app_name.strip().lower()
            cypher = """
                MATCH (t:Task)-[:TARGETED]->(a:App)
                WHERE lower(a.name) = $app_name OR contains(lower(a.name), $app_name) OR contains($app_name, lower(a.name))
                RETURN t.id, t.goal, t.summary, t.timestamp, t.duration_ms, t.total_steps, t.success, t.embedding
            """
            params = {"app_name": clean_app}
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
            clean_target = app.strip().lower()
            q_res = conn.execute(
                """
                MATCH (a:App)-[:EXHIBITS]->(q:AppQuirk)
                WHERE lower(a.name) = $app OR contains(lower(a.name), $app) OR contains($app, lower(a.name))
                RETURN a.name, q.issue, q.workaround, q.playbook
                """,
                {"app": clean_target},
            )
            while q_res.has_next():
                r = q_res.get_next()
                app_quirks.append({
                    "app": r[0],
                    "issue": r[1],
                    "workaround": r[2],
                    "playbook": r[3],
                })

        # 4. Check for active environmental session / browser profile
        session_info = None
        if app_name:
            session_info = recall_app_session(app_name, custom_db_path=custom_db_path)

        res_dict = {
            "query": query,
            "total_matches": len(enriched_results),
            "memories": enriched_results,
            "known_app_quirks": app_quirks,
        }
        if session_info:
            res_dict["active_session"] = session_info
        return res_dict

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
    if len(cond_clean) < 3:
        return None

    cache_key = f"{app_name or ''}:{cond_clean}"
    if custom_db_path is None and cache_key in _SOUL_DECISION_CACHE:
        return _SOUL_DECISION_CACHE[cache_key]

    try:
        conn = get_memory_connection(custom_db_path, max_retries=0)

        # 1. Match against past SoulDecisions (app-scoped if app_name provided)
        matched_row = None
        if app_name:
            clean_app = app_name.strip().lower()
            res = conn.execute(
                """
                MATCH (t:Task)-[:TARGETED]->(a:App), (t:Task)-[:DECIDED]->(d:SoulDecision)
                WHERE (lower(a.name) = $app OR contains(lower(a.name), $app) OR contains($app, lower(a.name)))
                  AND lower(d.condition) = lower($cond)
                  AND d.condition <> ''
                RETURN d.decision_type, d.result, d.confidence, d.context
                LIMIT 1
                """,
                {"app": clean_app, "cond": cond_clean},
            )
            if res.has_next():
                matched_row = res.get_next()

        # If no app specified, match against any valid SoulDecision with that condition
        if matched_row is None and not app_name:
            res = conn.execute(
                """
                MATCH (d:SoulDecision)
                WHERE lower(d.condition) = lower($cond)
                  AND d.condition <> ''
                RETURN d.decision_type, d.result, d.confidence, d.context
                LIMIT 1
                """,
                {"cond": cond_clean},
            )
            if res.has_next():
                matched_row = res.get_next()
        elif matched_row is None and app_name:
            # If app_name given but no app-specific decision exists, allow explicitly global/generic decisions
            res = conn.execute(
                """
                MATCH (d:SoulDecision)
                WHERE lower(d.condition) = lower($cond)
                  AND d.condition <> ''
                  AND (lower(d.context) CONTAINS 'global' OR lower(d.context) CONTAINS 'generic')
                RETURN d.decision_type, d.result, d.confidence, d.context
                LIMIT 1
                """,
                {"cond": cond_clean},
            )
            if res.has_next():
                matched_row = res.get_next()

        if matched_row is not None:
            ret = {
                "source": "prior_soul_decision",
                "decision_type": matched_row[0],
                "result": matched_row[1],
                "confidence": float(matched_row[2]),
                "context": matched_row[3],
            }
            if custom_db_path is None:
                _SOUL_DECISION_CACHE[cache_key] = ret
            return ret

        # 2. Match against AppQuirk if app_name given
        if app_name:
            clean_app = app_name.strip().lower()
            q_res = conn.execute(
                """
                MATCH (a:App)-[:EXHIBITS]->(q:AppQuirk)
                WHERE (lower(a.name) = $app_name OR contains(lower(a.name), $app_name) OR contains($app_name, lower(a.name)))
                  AND (lower(q.issue) CONTAINS lower($cond) OR lower(q.playbook) CONTAINS lower($cond))
                  AND q.issue <> ''
                RETURN q.issue, q.workaround, q.playbook
                LIMIT 1
                """,
                {"app_name": clean_app, "cond": cond_clean},
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


_APP_SESSION_CACHE: Dict[str, Optional[Dict[str, Any]]] = {}


def clear_app_session_cache() -> None:
    _APP_SESSION_CACHE.clear()


def recall_app_session(
    service_name: str,
    custom_db_path: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    """
    Sub-2ms instant recall for active browser profiles and authentication sessions.
    Returns matching session dict or None if not found.
    """
    clean_service = service_name.strip().lower()
    if custom_db_path is None and clean_service in _APP_SESSION_CACHE:
        return _APP_SESSION_CACHE[clean_service]

    try:
        conn = get_memory_connection(custom_db_path, max_retries=0)
        res = conn.execute(
            """
            MATCH (s:AppSession)
            WHERE lower(s.service_name) = lower($svc)
            RETURN s.service_name, s.browser, s.profile_name, s.profile_path, s.last_verified
            LIMIT 1
            """,
            {"svc": clean_service},
        )
        if res.has_next():
            row = res.get_next()
            ret = {
                "service_name": row[0],
                "browser": row[1],
                "profile_name": row[2],
                "profile_path": row[3],
                "last_verified": int(row[4]),
            }
            if custom_db_path is None:
                _APP_SESSION_CACHE[clean_service] = ret
            return ret
    except Exception as ex:
        logger.debug("Could not recall app session: %s", ex)

    if custom_db_path is None:
        _APP_SESSION_CACHE[clean_service] = None
    return None


