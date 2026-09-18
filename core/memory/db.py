"""
KùzuDB Database Manager for Extra Memory.
Manages the embedded episodic and relational graph store in ~/.extra/memory/.
"""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Any, Optional

try:
    import kuzu
except ImportError:
    kuzu = None

logger = logging.getLogger("Extra-Memory-DB")

_DB_LOCK = threading.Lock()
_KUZU_DB: Optional[Any] = None
_DB_PATH: Optional[Path] = None


def get_memory_dir() -> Path:
    """Returns the sovereign directory for Extra memory storage."""
    base_dir = Path.home() / ".extra" / "memory"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def get_default_db_path() -> Path:
    """Returns the default file path prefix for the Kùzu database."""
    return get_memory_dir() / "graph.kuzu"


def init_schema(conn: kuzu.Connection) -> None:
    """Idempotently initializes the node and relationship tables."""
    # 1. Nodes
    conn.execute("""
        CREATE NODE TABLE IF NOT EXISTS Task (
            id STRING,
            goal STRING,
            summary STRING,
            timestamp DOUBLE,
            duration_ms DOUBLE,
            total_steps INT64,
            success BOOLEAN,
            embedding FLOAT[384],
            PRIMARY KEY (id)
        )
    """)

    conn.execute("""
        CREATE NODE TABLE IF NOT EXISTS App (
            name STRING,
            exe_path STRING,
            ui_type STRING,
            PRIMARY KEY (name)
        )
    """)

    conn.execute("""
        CREATE NODE TABLE IF NOT EXISTS ActionStep (
            id STRING,
            step_num INT64,
            tool_name STRING,
            parameters STRING,
            duration_ms DOUBLE,
            PRIMARY KEY (id)
        )
    """)

    conn.execute("""
        CREATE NODE TABLE IF NOT EXISTS Artifact (
            id STRING,
            file_path STRING,
            mime_type STRING,
            size_bytes INT64,
            PRIMARY KEY (id)
        )
    """)

    conn.execute("""
        CREATE NODE TABLE IF NOT EXISTS StallEvent (
            id STRING,
            strike_count INT64,
            trigger_action STRING,
            resolution STRING,
            PRIMARY KEY (id)
        )
    """)

    conn.execute("""
        CREATE NODE TABLE IF NOT EXISTS AppQuirk (
            id STRING,
            issue STRING,
            workaround STRING,
            playbook STRING,
            PRIMARY KEY (id)
        )
    """)

    # 2. Relationships
    conn.execute("CREATE REL TABLE IF NOT EXISTS TARGETED (FROM Task TO App)")
    conn.execute("CREATE REL TABLE IF NOT EXISTS EXECUTED (FROM Task TO ActionStep)")
    conn.execute("CREATE REL TABLE IF NOT EXISTS PRODUCED (FROM Task TO Artifact)")
    conn.execute("CREATE REL TABLE IF NOT EXISTS ENCOUNTERED (FROM Task TO StallEvent)")
    conn.execute("CREATE REL TABLE IF NOT EXISTS EXHIBITS (FROM App TO AppQuirk)")
    conn.execute("CREATE REL TABLE IF NOT EXISTS REFINED_BY (FROM StallEvent TO AppQuirk)")

    logger.info("KùzuDB memory schema verified and initialized.")


def get_memory_db(custom_path: Optional[Path] = None) -> Any:
    """Returns or initializes the singleton Kùzu database instance."""
    if kuzu is None:
        raise RuntimeError("Kùzu is not installed. Run 'pip install kuzu' to enable Extra memory.")
    global _KUZU_DB, _DB_PATH
    with _DB_LOCK:
        target_path = custom_path or get_default_db_path()
        if _KUZU_DB is not None and _DB_PATH == target_path:
            return _KUZU_DB

        if _KUZU_DB is not None and _DB_PATH != target_path:
            del _KUZU_DB
            _KUZU_DB = None
            _DB_PATH = None
            import gc
            gc.collect()

        target_path.parent.mkdir(parents=True, exist_ok=True)
        db_str = str(target_path).replace("\\", "/")
        _KUZU_DB = kuzu.Database(db_str)
        _DB_PATH = target_path
        logger.info("Opened KùzuDB memory database at %s", target_path)

        # Initialize schema with connection
        conn = kuzu.Connection(_KUZU_DB)
        init_schema(conn)

        return _KUZU_DB


def get_memory_connection(custom_path: Optional[Path] = None) -> Any:
    """Returns a new thread-safe connection to the Kùzu database."""
    if kuzu is None:
        raise RuntimeError("Kùzu is not installed. Run 'pip install kuzu' to enable Extra memory.")
    db = get_memory_db(custom_path)
    return kuzu.Connection(db)


def close_memory_db() -> None:
    """Closes and releases the Kùzu database singleton."""
    global _KUZU_DB, _DB_PATH
    with _DB_LOCK:
        if _KUZU_DB is not None:
            del _KUZU_DB
            _KUZU_DB = None
        _DB_PATH = None
        import gc
        gc.collect()
        logger.info("Closed KùzuDB memory database.")
