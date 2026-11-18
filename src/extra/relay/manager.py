"""
Project Extra — Background Cloud Relay Lifecycle Manager.
Maintains persistent outbound WebSocket connectivity for remote AI agents (ChatGPT, Claude)
without requiring manual terminal executions of `extra connect`.
"""

import asyncio
import json
import logging
import os
import socket
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional

from extra.relay.client import (
    DEFAULT_RELAY_URL,
    get_default_device_name,
    run_relay_loop,
)

logger = logging.getLogger("extra.relay.manager")

_MANAGER_INSTANCE: Optional["RelayManager"] = None
_MANAGER_LOCK = threading.Lock()


class RelayManager:
    """
    Thread-safe singleton managing the outbound WebSocket relay tunnel.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = False
        self._status = "stopped"  # stopped, connecting, connected, reconnecting, disabled
        self._token: Optional[str] = None
        self._device_name: str = get_default_device_name()
        self._hub_url: str = DEFAULT_RELAY_URL
        self._last_heartbeat: float = 0.0
        self._last_error: Optional[str] = None
        self._stop_event: Optional[asyncio.Event] = None

    @classmethod
    def get_instance(cls) -> "RelayManager":
        global _MANAGER_INSTANCE
        with _MANAGER_LOCK:
            if _MANAGER_INSTANCE is None:
                _MANAGER_INSTANCE = cls()
            return _MANAGER_INSTANCE

    def _state_callback(self, state: str, error: Optional[str] = None) -> None:
        with self._lock:
            self._status = state
            if state == "connected":
                self._last_heartbeat = time.time()
                self._last_error = None
            elif state == "reconnecting":
                self._last_error = error
            elif state == "stopped":
                self._status = "stopped"

    def auto_start_if_configured(self) -> bool:
        """
        Reads local configuration (~/.extra/config.json).
        If user is signed in with a valid relay token and not in local-only mode,
        starts the background relay automatically.
        """
        try:
            cfg_path = Path.home() / ".extra" / "config.json"
            if not cfg_path.exists():
                return False

            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if data.get("is_local_mode", False):
                with self._lock:
                    self._status = "disabled"
                logger.info("Local air-gapped mode active; cloud relay not started.")
                return False

            token = data.get("relay_token")
            if token and token != "anonymous" and len(token) > 10:
                logger.info("Auto-starting cloud relay with stored credentials...")
                return self.start(token=token)

            return False
        except Exception as e:
            logger.warning("Error reading config for auto-start: %s", e)
            return False

    def is_running(self) -> bool:
        """Returns True if the background relay worker thread is currently active."""
        with self._lock:
            return self._running

    def _stop_locked(self) -> None:
        if not self._running:
            self._status = "stopped"
            return
        self._status = "stopped"
        self._running = False
        if self._loop and self._loop.is_running():
            try:
                self._loop.call_soon_threadsafe(self._loop.stop)
            except Exception:
                pass

    def start(self, token: Optional[str] = None, device_name: Optional[str] = None, force: bool = False) -> bool:
        """
        Starts the background WebSocket relay tunnel.
        """
        with self._lock:
            token_changed = (token is not None and self._token is not None and token != self._token)
            if token is not None:
                self._token = token
            elif not self._token:
                # Try reading from config.json
                try:
                    cfg_path = Path.home() / ".extra" / "config.json"
                    if cfg_path.exists():
                        with open(cfg_path, "r", encoding="utf-8") as f:
                            self._token = json.load(f).get("relay_token")
                except Exception:
                    pass

            if not self._token or self._token == "anonymous":
                self._status = "stopped"
                self._last_error = "No relay passkey configured. Please sign in to connect to Cloud Hub."
                return False

            if device_name:
                self._device_name = device_name

            # Check if running and already connected with the same token
            is_active = self._running and self._thread and self._thread.is_alive()
            needs_restart = (
                not is_active
                or token_changed
                or force
                or self._status != "connected"
            )

            if not needs_restart:
                logger.info("RelayManager already running and connected.")
                return True

            if is_active:
                logger.info("RelayManager restarting tunnel (token_changed=%s, status=%s)...", token_changed, self._status)
                self._stop_locked()

            # Wait briefly for old thread to finish if still alive to prevent state race condition
            old_thread = self._thread
            if old_thread and old_thread.is_alive() and threading.current_thread() != old_thread:
                try:
                    old_thread.join(timeout=1.0)
                except Exception:
                    pass

            self._running = True
            self._status = "connecting"
            self._last_error = None

            def _worker() -> None:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
                try:
                    logger.info("Relay worker loop active for device %s", self._device_name)
                    self._loop.run_until_complete(
                        run_relay_loop(
                            hub_url=self._hub_url,
                            token=self._token,  # type: ignore
                            device_name=self._device_name,
                            on_state_change=self._state_callback,
                        )
                    )
                except Exception as ex:
                    logger.error("Relay worker loop exited with exception: %s", ex)
                    with self._lock:
                        self._last_error = str(ex)
                finally:
                    with self._lock:
                        self._running = False
                        self._status = "stopped"
                    if self._loop and not self._loop.is_closed():
                        self._loop.close()

            self._thread = threading.Thread(
                target=_worker,
                daemon=True,
                name="Extra-CloudRelay-Daemon",
            )
            self._thread.start()
            return True

    def stop(self) -> bool:
        """
        Gracefully disconnects and terminates the background relay loop.
        """
        with self._lock:
            if not self._running:
                self._status = "stopped"
                return True

            self._status = "stopped"
            self._running = False
            if self._loop and self._loop.is_running():
                try:
                    self._loop.call_soon_threadsafe(self._loop.stop)
                except Exception:
                    pass

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)
        logger.info("RelayManager stopped successfully.")
        return True

    def get_status(self) -> Dict[str, Any]:
        """
        Returns full telemetry regarding active relay connectivity.
        """
        with self._lock:
            is_alive = bool(self._running and self._thread and self._thread.is_alive())
            connected = is_alive and self._status == "connected"
            has_token = bool(self._token and self._token != "anonymous")

            cloud_mcp_url = None
            if has_token:
                cloud_mcp_url = f"https://extra.yantraos.com/mcp?key={self._token}"

            return {
                "running": is_alive,
                "status": self._status if is_alive else ("disabled" if self._status == "disabled" else "stopped"),
                "connected": connected,
                "token_configured": has_token,
                "device_name": self._device_name,
                "hub_url": self._hub_url,
                "cloud_mcp_url": cloud_mcp_url,
                "cloud_sse_url": "https://extra.yantraos.com/sse",
                "last_heartbeat": self._last_heartbeat,
                "last_error": self._last_error,
                "timestamp": time.time(),
            }

    def ping(self) -> Dict[str, Any]:
        """
        Tests round-trip reachability to the AWS cloud hub and reports local tunnel status.
        """
        with self._lock:
            local_connected = bool(self._running and self._status == "connected")

        start = time.perf_counter()
        try:
            import urllib.request
            # Health probe against HTTPS endpoint
            req = urllib.request.Request(
                "https://extra.yantraos.com/health",
                headers={"User-Agent": "Extra-Desktop/0.3.6"},
            )
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
                return {
                    "ok": resp.status in (200, 204),
                    "status_code": resp.status,
                    "latency_ms": elapsed_ms,
                    "cloud_reachable": True,
                    "connected": local_connected,
                }
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
            return {
                "ok": False,
                "latency_ms": elapsed_ms,
                "cloud_reachable": False,
                "connected": local_connected,
                "error": str(e),
            }
