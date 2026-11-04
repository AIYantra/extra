# ExtraApp — State, Persistence & Memory Specification (MEMORY.md)
**Storage Location:** `%USERPROFILE%\.extra\station\` (Windows) / `~/.extra/station/` (macOS/Linux)  
**Format:** JSON / SQLite3 (Zero cloud dependency, 100% sovereign)  
**Compliance:** Windows Defender Controlled Folder Access (CFA) Compliant  

---

## 1. Storage Architecture Overview

ExtraApp maintains persistent state strictly within the user's isolated `.extra` directory. It never writes to protected system directories (`Documents`, `Program Files`, `Pictures`) ensuring zero security warnings or permission blocks:

```
~/.extra/
  ├── venv/                         # Dedicated Python virtual environment
  ├── station/                      # ExtraApp GUI persistent state
  │   ├── config.json               # User preferences & window state
  │   ├── impact_ledger.json        # Cumulative token & cost savings
  │   ├── audit.db                  # Local SQLite circular audit trail
  │   └── cache/                    # Perception thumbnail buffer (max 10 MB)
```

---

## 2. Configuration Schema (`config.json`)

```json
{
  "$schema": "https://extra.yantraos.com/schemas/station-config-v1.json",
  "version": "1.0.0",
  "general": {
    "launch_on_startup": true,
    "start_minimized_to_tray": true,
    "theme": "dark",
    "global_panic_hotkey": "Ctrl+Alt+Escape",
    "panic_sound_feedback": true
  },
  "window": {
    "mode": "tray_popup",
    "width": 440,
    "height": 640,
    "expanded_width": 960,
    "expanded_height": 680,
    "always_on_top": false
  },
  "engine_connection": {
    "host": "127.0.0.1",
    "port": 8000,
    "auto_reconnect": true,
    "heartbeat_interval_ms": 1000
  },
  "notifications": {
    "notify_on_task_start": false,
    "notify_on_task_complete": true,
    "notify_on_panic_stop": true
  }
}
```

---

## 3. Impact Ledger Schema (`impact_ledger.json`)

The Impact Ledger tracks cumulative savings achieved by using Extra's dual-plane architecture (Plane B UIA COM instead of sending full-resolution vision screenshots to LLMs):

```json
{
  "lifetime_metrics": {
    "total_tasks_executed": 342,
    "vision_tokens_saved": 4820150,
    "api_dollars_saved_usd": 62.45,
    "execution_time_saved_seconds": 4320,
    "average_latency_ms": 14.2
  },
  "monthly_rollups": {
    "2026-10": {
      "tasks": 84,
      "tokens_saved": 1420500,
      "cost_saved_usd": 18.42,
      "time_saved_sec": 1280
    }
  },
  "client_breakdown": {
    "cursor": { "tasks": 210, "tokens_saved": 3120000 },
    "claude_desktop": { "tasks": 98, "tokens_saved": 1240000 },
    "windsurf": { "tasks": 34, "tokens_saved": 460150 }
  }
}
```

---

## 4. Audit Log Buffer (`audit.db`)

Extra Station persists an append-only, high-performance circular SQLite database of all executed computer-use actions.

### Schema:
```sql
CREATE TABLE IF NOT EXISTS action_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    client_name TEXT NOT NULL,         -- 'cursor', 'claude_desktop', 'windsurf'
    tool_name TEXT NOT NULL,           -- 'extra_click', 'extra_type', 'extra_inspect_ui'
    plane_used TEXT NOT NULL,          -- 'visual_dxgi', 'semantic_uia', 'win32_input'
    target_window TEXT,                -- 'Calculator', 'Google Chrome'
    details JSON,                      -- Action arguments & coordinates
    duration_ms REAL NOT NULL,         -- Sub-millisecond latency
    outcome TEXT NOT NULL              -- 'success', 'settled', 'aborted', 'error'
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON action_audit_log(timestamp DESC);
```

### Retention Policy:
- Maximum buffer size: **5,000 entries** or **30 days**.
- Automatic pruning occurs upon startup to guarantee the database never exceeds 5 MB on disk.

---

## 5. Security & Isolation Invariants

1. **Local-Only Boundary:** The Station's memory files are never synced to any remote server or third-party cloud.
2. **Sanitization:** Action arguments in `details` automatically redact sensitive fields (e.g. passwords, bearer tokens) before writing to the audit database.
3. **Atomic Writes:** All JSON configuration writes utilize write-to-temp-and-rename semantics (`fs::write(temp) -> fs::rename(dest)`) preventing corruption during power cuts or abrupt shutdowns.
