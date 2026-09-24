"""
Extra Memory Subsystem — Local Episodic & Relational Knowledge Graph
Powered by KùzuDB and FastEmbed for sovereign, sub-millisecond memory recall.
"""

from extra.core.memory.db import get_memory_db, get_memory_connection, close_memory_db
from extra.core.memory.embeddings import get_embedding, cosine_similarity
from extra.core.memory.ingest import (
    get_active_recorder,
    TaskMemoryRecorder,
    start_memory_recording,
    finish_memory_recording,
    record_action_step,
    record_action_app,
    record_action_artifact,
    record_action_stall,
    record_action_quirk,
    record_action_soul_decision,
)
from extra.core.memory.recall import recall_memory, recall_soul_decision

__all__ = [
    "get_memory_db",
    "get_memory_connection",
    "close_memory_db",
    "get_embedding",
    "cosine_similarity",
    "get_active_recorder",
    "TaskMemoryRecorder",
    "start_memory_recording",
    "finish_memory_recording",
    "record_action_step",
    "record_action_app",
    "record_action_artifact",
    "record_action_stall",
    "record_action_quirk",
    "record_action_soul_decision",
    "recall_memory",
    "recall_soul_decision",
]
