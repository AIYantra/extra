"""
Project Extra — Sovereign Execution Mode Controller
Manages runtime acceleration profiles: 'turbo' (low latency), 'balanced' (medium), and 'smart' (high verification).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union


class ExecutionMode(str, Enum):
    TURBO = "turbo"        # Fast / Fire-and-forget / Minimal delays (< 15ms)
    BALANCED = "balanced"  # Default / Adaptive SOUL settle / Compact UI (~100ms)
    SMART = "smart"        # Full closed-loop verification / UIA + Pixel diffing / Memory recall (~400ms)

    @classmethod
    def from_string(cls, val: Union[str, ExecutionMode]) -> ExecutionMode:
        if isinstance(val, ExecutionMode):
            return val
        s = str(val).strip().lower()
        if s in ("turbo", "fast", "low", "lightning", "speed", "l"):
            return cls.TURBO
        if s in ("smart", "high", "deep", "full", "verify", "safe", "h"):
            return cls.SMART
        return cls.BALANCED


@dataclass
class ModeConfig:
    mode: ExecutionMode
    auto_settle: bool
    settle_timeout_sec: float
    max_inspect_elements: int
    compact_ui: bool
    strip_heavy_attributes: bool
    sleep_scale: float
    max_sleep_ms: float
    proactive_memory_recall: bool
    dual_plane_verification: bool

    @property
    def name(self) -> ExecutionMode:
        return self.mode

    def scale_sleep(self, duration_ms: float) -> float:
        """Scales requested sleep duration (in milliseconds) according to mode profile."""
        scaled = float(duration_ms) * self.sleep_scale
        return min(scaled, self.max_sleep_ms)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["mode"] = self.mode.value
        return d


MODE_PROFILES: Dict[ExecutionMode, ModeConfig] = {
    ExecutionMode.TURBO: ModeConfig(
        mode=ExecutionMode.TURBO,
        auto_settle=False,
        settle_timeout_sec=0.5,
        max_inspect_elements=10,
        compact_ui=True,
        strip_heavy_attributes=True,
        sleep_scale=0.05,
        max_sleep_ms=50.0,
        proactive_memory_recall=False,
        dual_plane_verification=False,
    ),
    ExecutionMode.BALANCED: ModeConfig(
        mode=ExecutionMode.BALANCED,
        auto_settle=True,
        settle_timeout_sec=1.5,
        max_inspect_elements=15,
        compact_ui=True,
        strip_heavy_attributes=True,
        sleep_scale=0.5,
        max_sleep_ms=500.0,
        proactive_memory_recall=False,
        dual_plane_verification=False,
    ),
    ExecutionMode.SMART: ModeConfig(
        mode=ExecutionMode.SMART,
        auto_settle=True,
        settle_timeout_sec=4.0,
        max_inspect_elements=30,
        compact_ui=False,
        strip_heavy_attributes=False,
        sleep_scale=1.0,
        max_sleep_ms=10000.0,
        proactive_memory_recall=True,
        dual_plane_verification=True,
    ),
}

_active_mode: ExecutionMode = ExecutionMode.from_string(os.environ.get("EXTRA_SPEED_MODE", "balanced"))


def get_execution_mode() -> ExecutionMode:
    """Returns currently active global ExecutionMode."""
    return _active_mode


def set_execution_mode(mode: Union[str, ExecutionMode], persist: bool = False) -> ModeConfig:
    """Sets active ExecutionMode and optionally persists to ~/.extra/config.json."""
    global _active_mode
    _active_mode = ExecutionMode.from_string(mode)
    os.environ["EXTRA_SPEED_MODE"] = _active_mode.value
    if persist:
        try:
            cfg_path = Path.home() / ".extra" / "config.json"
            cfg_path.parent.mkdir(parents=True, exist_ok=True)
            data: Dict[str, Any] = {}
            if cfg_path.exists():
                try:
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = {}
            data["speed_mode"] = _active_mode.value
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass
    return MODE_PROFILES[_active_mode]


def get_mode_config(mode: Optional[Union[str, ExecutionMode]] = None) -> ModeConfig:
    """Returns ModeConfig for given mode, or active mode if None."""
    if mode is not None:
        resolved = ExecutionMode.from_string(mode)
        return MODE_PROFILES[resolved]
    return MODE_PROFILES[_active_mode]
