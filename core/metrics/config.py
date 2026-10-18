"""
Configuration and privacy consent engine for Project Extra metrics and telemetry.
Manages user preferences in ~/.extra/config.json with strict privacy-by-design defaults.
"""

import os
import json
import uuid
import hashlib
import platform
from pathlib import Path
from typing import Dict, Any, Optional

EXTRA_HOME = Path.home() / ".extra"
CONFIG_PATH = EXTRA_HOME / "config.json"
METRICS_DIR = EXTRA_HOME / "metrics"
LEDGER_PATH = METRICS_DIR / "impact_ledger.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "version": "1.0",
    "telemetry_enabled": False,
    "telemetry_prompted": False,
    "first_run_recorded": False,
    "anonymous_machine_id": "",
    "created_at": "",
    "updated_at": ""
}

def get_config_path() -> Path:
    """Returns the absolute path to ~/.extra/config.json."""
    return CONFIG_PATH

def get_metrics_dir() -> Path:
    """Ensures and returns the metrics storage directory ~/.extra/metrics/."""
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    return METRICS_DIR

def get_ledger_path() -> Path:
    """Returns the absolute path to ~/.extra/metrics/impact_ledger.json."""
    get_metrics_dir()
    return LEDGER_PATH

def _generate_anonymous_machine_id() -> str:
    """
    Generates a one-way salt-hashed machine identifier.
    Uses platform node and a system salt, returning sha256 hex digest.
    Zero identifiable personal data or IP address is encoded.
    """
    salt = "extra_sovereign_desktop_v1"
    raw_id = f"{platform.node()}:{platform.machine()}:{uuid.getnode()}:{salt}"
    return hashlib.sha256(raw_id.encode("utf-8")).hexdigest()

def load_config() -> Dict[str, Any]:
    """Loads ~/.extra/config.json or initializes default configuration."""
    if not CONFIG_PATH.is_file():
        cfg = DEFAULT_CONFIG.copy()
        cfg["anonymous_machine_id"] = _generate_anonymous_machine_id()
        save_config(cfg)
        return cfg
    
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        # Ensure required keys exist
        for k, v in DEFAULT_CONFIG.items():
            if k not in data:
                data[k] = v
        if not data.get("anonymous_machine_id"):
            data["anonymous_machine_id"] = _generate_anonymous_machine_id()
            save_config(data)
        return data
    except Exception:
        cfg = DEFAULT_CONFIG.copy()
        cfg["anonymous_machine_id"] = _generate_anonymous_machine_id()
        return cfg

def save_config(config_data: Dict[str, Any]) -> None:
    """Saves configuration atomically to ~/.extra/config.json."""
    EXTRA_HOME.mkdir(parents=True, exist_ok=True)
    temp_path = CONFIG_PATH.with_suffix(".tmp")
    try:
        temp_path.write_text(json.dumps(config_data, indent=2), encoding="utf-8")
        temp_path.replace(CONFIG_PATH)
    except Exception:
        # Fallback direct write
        CONFIG_PATH.write_text(json.dumps(config_data, indent=2), encoding="utf-8")

def is_telemetry_enabled() -> bool:
    """
    Determines whether fleet telemetry is legally and explicitly enabled.
    
    Priority Order:
    1. DO_NOT_TRACK == "1" -> False (Strict universal privacy override)
    2. EXTRA_TELEMETRY in ("0", "false", "off", "no") -> False (Explicit env override)
    3. EXTRA_TELEMETRY in ("1", "true", "on", "yes") -> True (Explicit env override)
    4. ~/.extra/config.json ["telemetry_enabled"] -> bool
    5. Fallback Default -> False (100% air-gapped local mode)
    """
    # 1. Universal DO_NOT_TRACK standard
    if os.environ.get("DO_NOT_TRACK") == "1":
        return False
    
    # 2. Explicit Extra env var override
    env_val = os.environ.get("EXTRA_TELEMETRY", "").strip().lower()
    if env_val in ("0", "false", "off", "no"):
        return False
    if env_val in ("1", "true", "on", "yes"):
        return True
    
    # 3. User configuration file
    cfg = load_config()
    return bool(cfg.get("telemetry_enabled", False))

def set_telemetry_enabled(enabled: bool) -> None:
    """Explicitly toggles the telemetry consent flag in configuration."""
    cfg = load_config()
    cfg["telemetry_enabled"] = bool(enabled)
    cfg["telemetry_prompted"] = True
    save_config(cfg)

def get_anonymous_machine_id() -> str:
    """Returns the persistent, anonymous one-way hashed machine identifier."""
    cfg = load_config()
    return cfg.get("anonymous_machine_id") or _generate_anonymous_machine_id()

def is_first_run_pending() -> bool:
    """Returns True if the one-time first-run activation has not been recorded."""
    cfg = load_config()
    return not bool(cfg.get("first_run_recorded", False))

def mark_first_run_complete() -> None:
    """Marks the first-run activation flag as recorded in configuration."""
    cfg = load_config()
    cfg["first_run_recorded"] = True
    save_config(cfg)

def is_first_run_telemetry_allowed() -> bool:
    """
    Checks if anonymous first-run activation telemetry is permitted.
    Strictly honors DO_NOT_TRACK=1 and EXTRA_TELEMETRY=0/off/false/no.
    """
    if os.environ.get("DO_NOT_TRACK") == "1":
        return False
    env_val = os.environ.get("EXTRA_TELEMETRY", "").strip().lower()
    if env_val in ("0", "false", "off", "no"):
        return False
    return True

