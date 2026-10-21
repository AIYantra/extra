"""
Privacy-Preserving Telemetry Client for Project Extra.
Handles non-blocking, asynchronous event dispatch to the telemetry ingest endpoint.
Guarantees 100% silent no-op when telemetry is disabled or in air-gapped mode.
"""

import os
import json
import time
import platform
import urllib.request
import urllib.error
from threading import Thread, Lock
from typing import Dict, Any, List, Optional

from extra.core.metrics.config import (
    is_telemetry_enabled,
    get_anonymous_machine_id,
    is_first_run_pending,
    mark_first_run_complete,
    is_first_run_telemetry_allowed
)
from extra.core.metrics.sanitizer import ZeroPiiSanitizer

DEFAULT_TELEMETRY_ENDPOINT = "https://extra.yantraos.com/api/telemetry"

class TelemetryClient:
    """Non-blocking background telemetry client with zero-PII guarantees."""

    _instance: Optional["TelemetryClient"] = None
    _lock = Lock()

    def __init__(self, endpoint_url: Optional[str] = None):
        self.endpoint_url = endpoint_url or os.environ.get("EXTRA_TELEMETRY_ENDPOINT", DEFAULT_TELEMETRY_ENDPOINT)
        self.queue: List[Dict[str, Any]] = []
        self.queue_lock = Lock()
        self.is_flushing = False

    @classmethod
    def get_instance(cls) -> "TelemetryClient":
        """Singleton accessor for global telemetry client."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def emit_event(
        self,
        app: str,
        archetype: str,
        tool_name: str,
        compilation_latency_ms: float = 0.0,
        execution_duration_ms: float = 0.0,
        settle_latency_ms: float = 0.0,
        actions_count: int = 1,
        success: bool = True,
        error_class: Optional[str] = None,
        speedup: float = 1.0
    ) -> bool:
        """
        Emits an anonymized execution event if telemetry is explicitly enabled.
        Returns True if event was queued, False if telemetry is disabled.
        """
        if not is_telemetry_enabled():
            return False

        try:
            client_hash = get_anonymous_machine_id()
            payload = ZeroPiiSanitizer.build_telemetry_event(
                client_hash=client_hash,
                app=app,
                archetype=archetype,
                tool_name=tool_name,
                compilation_latency_ms=compilation_latency_ms,
                execution_duration_ms=execution_duration_ms,
                settle_latency_ms=settle_latency_ms,
                actions_count=actions_count,
                success=success,
                error_class=error_class,
                speedup=speedup
            )

            with self.queue_lock:
                self.queue.append(payload)
                # Keep queue capped at 50 to prevent unbounded memory growth if offline
                if len(self.queue) > 50:
                    self.queue = self.queue[-50:]

            # Trigger non-blocking async dispatch
            self._trigger_async_flush()
            return True
        except Exception:
            # Telemetry failures must NEVER interrupt execution
            return False

    def _trigger_async_flush(self) -> None:
        """Dispatches an asynchronous daemon thread to flush queued events."""
        with self.queue_lock:
            if self.is_flushing or not self.queue:
                return
            self.is_flushing = True

        t = Thread(target=self._flush_worker, daemon=True)
        t.start()

    def _flush_worker(self) -> None:
        """Background thread worker sending buffered events."""
        try:
            with self.queue_lock:
                events_to_send = list(self.queue)
                self.queue.clear()

            if not events_to_send:
                return

            req_data = json.dumps({"events": events_to_send}).encode("utf-8")
            req = urllib.request.Request(
                self.endpoint_url,
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Extra-Telemetry/0.3.1"
                },
                method="POST"
            )

            # Strict 2.0-second timeout to avoid any thread hang
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                pass
        except Exception:
            # Silently drop failed sends to maintain strict air-gap resiliency
            pass
        finally:
            with self.queue_lock:
                self.is_flushing = False

    def flush_sync(self, timeout_sec: float = 2.0) -> bool:
        """Synchronously flushes queued events (used primarily in tests/shutdown)."""
        if not is_telemetry_enabled():
            return False

        with self.queue_lock:
            events_to_send = list(self.queue)
            self.queue.clear()

        if not events_to_send:
            return True

        try:
            req_data = json.dumps({"events": events_to_send}).encode("utf-8")
            req = urllib.request.Request(
                self.endpoint_url,
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                return resp.status in (200, 201, 204)
        except Exception:
            return False


def emit_first_run_activation(
    entrypoint: str = "mcp",
    endpoint_url: Optional[str] = None,
    sync: bool = False
) -> bool:
    """
    Emits a one-time anonymous first-run activation event.
    Guarantees:
    - Triggers at most once per machine (gated by config.json: first_run_recorded).
    - Strictly honors DO_NOT_TRACK=1 and EXTRA_TELEMETRY=0.
    - Zero personal identifiable information (zero username, zero IP, zero prompt data).
    - Completely non-blocking asynchronous dispatch (daemon thread, 2.0s timeout).
    - Fails silently on network errors or in air-gapped environments.

    Returns True if an activation event was dispatched or queued, False if skipped/disabled.
    """
    try:
        if not is_first_run_pending():
            return False

        if not is_first_run_telemetry_allowed():
            mark_first_run_complete()
            return False

        try:
            from extra import __version__
        except Exception:
            __version__ = "0.3.1"

        client_hash = get_anonymous_machine_id()
        payload = {
            "event": "activation_first_run",
            "client_hash": client_hash,
            "os": platform.system().lower(),
            "os_release": platform.release(),
            "arch": platform.machine(),
            "extra_version": __version__,
            "entrypoint": entrypoint,
            "timestamp": int(time.time()),
        }

        # Atomically record completion so it never fires again
        mark_first_run_complete()

        target_url = endpoint_url or os.environ.get("EXTRA_TELEMETRY_ENDPOINT", DEFAULT_TELEMETRY_ENDPOINT)

        def _worker() -> None:
            try:
                req_data = json.dumps({"events": [payload]}).encode("utf-8")
                req = urllib.request.Request(
                    target_url,
                    data=req_data,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": f"Extra-Activation/{__version__}",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    pass
            except Exception:
                pass

        if sync:
            try:
                req_data = json.dumps({"events": [payload]}).encode("utf-8")
                req = urllib.request.Request(
                    target_url,
                    data=req_data,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": f"Extra-Activation/{__version__}",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    return resp.status in (200, 201, 204)
            except Exception:
                return False

        t = Thread(target=_worker, daemon=True)
        t.start()
        return True
    except Exception:
        return False

