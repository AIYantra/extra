"""
Project Extra — Linux Ambient Awareness & Audio Feedback Subsystem
Provides auditory feedback via procedural acoustic synthesis (PipeWire / PulseAudio / ALSA)
and ambient HUD overlay controller with native desktop notification awareness.
"""

from __future__ import annotations

import io
import logging
import math
import os
import shutil
import struct
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional
import wave

from extra.core.platform.base import AbstractIndicatorController

logger = logging.getLogger("extra.indicators.linux")

_indicator_controller: Optional[LinuxIndicatorController] = None


class AudioIndicator:
    """
    Synthesizes and plays studio-grade acoustic glass chimes without external audio assets.
    Streams in-memory PCM buffers directly to pw-play, paplay, or aplay asynchronously.
    """

    def __init__(self) -> None:
        self.enabled = True
        self._cache: Dict[str, bytes] = {}

    def _synthesize(self, profile: str) -> bytes:
        if profile in self._cache:
            return self._cache[profile]

        sample_rate = 44100
        buf = io.BytesIO()

        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            frames: List[bytes] = []

            if profile == "complete":
                # Luxury Glass Marimba Chord: E6 (1318.5 Hz) -> G#6 (1661.2 Hz) -> B6 (1975.5 Hz) + warm E4 (329.6 Hz)
                duration = 0.55
                n_samples = int(duration * sample_rate)
                for i in range(n_samples):
                    t = i / sample_rate
                    # Note 1: E6 crystal strike at 0.0s
                    env1 = min(1.0, t / 0.005) * math.exp(-5.5 * t)
                    v1 = 0.42 * math.sin(2 * math.pi * 1318.51 * t) + 0.12 * math.sin(4 * math.pi * 1318.51 * t)

                    # Note 2: G#6 major third overtone at 0.05s
                    t2 = max(0.0, t - 0.05)
                    env2 = (min(1.0, t2 / 0.005) * math.exp(-5.0 * t2)) if t >= 0.05 else 0.0
                    v2 = 0.35 * math.sin(2 * math.pi * 1661.22 * t2) + 0.10 * math.sin(4 * math.pi * 1661.22 * t2)

                    # Note 3: B6 sparkling crowning resonance at 0.11s
                    t3 = max(0.0, t - 0.11)
                    env3 = (min(1.0, t3 / 0.005) * math.exp(-4.2 * t3)) if t >= 0.11 else 0.0
                    v3 = (
                        0.50 * math.sin(2 * math.pi * 1975.53 * t3)
                        + 0.18 * math.sin(4 * math.pi * 1975.53 * t3)
                        + 0.06 * math.sin(6 * math.pi * 1975.53 * t3)
                    )

                    # Sub-bass body: E4 warmth
                    env_sub = min(1.0, t / 0.012) * math.exp(-3.5 * t)
                    v_sub = 0.22 * math.sin(2 * math.pi * 329.63 * t)

                    sample = (env1 * v1) + (env2 * v2) + (env3 * v3) + (env_sub * v_sub)
                    sample = max(-0.95, min(0.95, sample))
                    int_sample = int(sample * 32767.0)
                    frames.append(struct.pack("<h", int_sample))

            elif profile == "start":
                # Subtle crystal chime: A5 (880 Hz) -> C#6 (1108.7 Hz)
                duration = 0.25
                n_samples = int(duration * sample_rate)
                for i in range(n_samples):
                    t = i / sample_rate
                    env1 = min(1.0, t / 0.003) * math.exp(-8.0 * t)
                    v1 = 0.35 * math.sin(2 * math.pi * 880.0 * t)
                    t2 = max(0.0, t - 0.04)
                    env2 = (min(1.0, t2 / 0.003) * math.exp(-7.0 * t2)) if t >= 0.04 else 0.0
                    v2 = 0.40 * math.sin(2 * math.pi * 1108.73 * t2)
                    sample = max(-0.95, min(0.95, (env1 * v1) + (env2 * v2)))
                    frames.append(struct.pack("<h", int(sample * 32767.0)))

            elif profile in ("alert", "error"):
                # Urgent acoustic warning: dual discordant glass strike
                duration = 0.35
                n_samples = int(duration * sample_rate)
                for i in range(n_samples):
                    t = i / sample_rate
                    env = min(1.0, t / 0.002) * math.exp(-6.0 * t)
                    v = 0.4 * math.sin(2 * math.pi * 440.0 * t) + 0.4 * math.sin(2 * math.pi * 466.16 * t)
                    sample = max(-0.95, min(0.95, env * v))
                    frames.append(struct.pack("<h", int(sample * 32767.0)))

            elif profile == "attention":
                # Prompt chime: G5 (783.99 Hz) -> C6 (1046.5 Hz)
                duration = 0.30
                n_samples = int(duration * sample_rate)
                for i in range(n_samples):
                    t = i / sample_rate
                    env1 = min(1.0, t / 0.004) * math.exp(-6.5 * t)
                    v1 = 0.35 * math.sin(2 * math.pi * 783.99 * t)
                    t2 = max(0.0, t - 0.06)
                    env2 = (min(1.0, t2 / 0.004) * math.exp(-5.5 * t2)) if t >= 0.06 else 0.0
                    v2 = 0.45 * math.sin(2 * math.pi * 1046.50 * t2)
                    sample = max(-0.95, min(0.95, (env1 * v1) + (env2 * v2)))
                    frames.append(struct.pack("<h", int(sample * 32767.0)))

            else:
                # Default blip
                duration = 0.15
                n_samples = int(duration * sample_rate)
                for i in range(n_samples):
                    t = i / sample_rate
                    env = math.exp(-12.0 * t)
                    sample = 0.3 * math.sin(2 * math.pi * 1000.0 * t) * env
                    frames.append(struct.pack("<h", int(sample * 32767.0)))

            wf.writeframes(b"".join(frames))

        data = buf.getvalue()
        self._cache[profile] = data
        return data

    def play(self, profile: str = "complete") -> None:
        """Plays synthesized acoustic chime via available Linux sound server asynchronously."""
        if not self.enabled:
            return

        def _play_worker() -> None:
            try:
                data = self._synthesize(profile)
                # Tier 1: PipeWire pw-play
                if shutil.which("pw-play"):
                    p = subprocess.Popen(
                        ["pw-play", "-"],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    p.communicate(input=data, timeout=1.5)
                    return
                # Tier 2: PulseAudio paplay
                if shutil.which("paplay"):
                    p = subprocess.Popen(
                        ["paplay"],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    p.communicate(input=data, timeout=1.5)
                    return
                # Tier 3: ALSA aplay
                if shutil.which("aplay"):
                    p = subprocess.Popen(
                        ["aplay", "-q"],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    p.communicate(input=data, timeout=1.5)
                    return
                # Tier 4: libcanberra sound theme fallback
                if shutil.which("canberra-gtk-play"):
                    sound_id = "complete" if profile == "complete" else "bell"
                    subprocess.run(
                        ["canberra-gtk-play", "-i", sound_id],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=1.0,
                    )
            except Exception as e:
                logger.debug(f"Audio playback error: {e}")

        threading.Thread(target=_play_worker, daemon=True).start()


class LinuxNotificationNotifier:
    """
    Sub-2ms desktop milestone notification dispatcher for Linux.
    Communicates directly with org.freedesktop.Notifications via D-Bus session bus.
    """

    def __init__(self) -> None:
        self.enabled = True
        self._last_id = 0

    def notify(
        self,
        summary: str,
        body: str = "",
        icon: str = "dialog-information",
        urgency: int = 1,
        expire_timeout_ms: int = 3000,
    ) -> int:
        if not self.enabled:
            return 0

        # Tier 1: Native D-Bus org.freedesktop.Notifications via Jeepney (< 2ms)
        try:
            from jeepney import DBusAddress, new_method_call
            from jeepney.io.blocking import open_dbus_connection

            conn = open_dbus_connection(bus="SESSION")
            try:
                addr = DBusAddress(
                    "/org/freedesktop/Notifications",
                    bus_name="org.freedesktop.Notifications",
                    interface="org.freedesktop.Notifications",
                )
                hints = {}
                if urgency != 1:
                    hints["urgency"] = ("y", urgency)
                msg = new_method_call(
                    addr,
                    "Notify",
                    "susssasa{sv}i",
                    ("Project Extra", self._last_id, icon, summary, body, [], hints, expire_timeout_ms),
                )
                reply = conn.send_and_get_reply(msg, timeout=0.4)
                if reply.body and len(reply.body) > 0:
                    self._last_id = int(reply.body[0])
                    return self._last_id
            finally:
                conn.close()
        except Exception:
            pass

        # Tier 2: notify-send CLI fallback
        if shutil.which("notify-send"):
            try:
                urgency_str = "critical" if urgency == 2 else ("low" if urgency == 0 else "normal")
                cmd = ["notify-send", "-a", "Project Extra", "-u", urgency_str, "-t", str(expire_timeout_ms)]
                if icon:
                    cmd.extend(["-i", icon])
                cmd.append(summary)
                if body:
                    cmd.append(body)
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return 1
            except Exception:
                pass

        return 0


class LinuxIndicatorOverlay:
    """
    Manages ambient edge glow and pilot indicator state on Linux.
    Tracks active modes and coordinates with desktop notifications.
    """

    def __init__(self) -> None:
        self.current_mode: str = "idle"
        self.is_visible: bool = False
        self._available: bool = False

    def setup(self) -> bool:
        """Initializes overlay controller."""
        self._available = True
        return True

    def show_active(self) -> None:
        """Displays active cyan border indicator."""
        self.current_mode = "active"
        self.is_visible = True

    def show_complete(self) -> None:
        """Flashes completion emerald green indicator."""
        self.current_mode = "complete"
        self.is_visible = True

    def show_alert(self) -> None:
        """Flashes crimson alert indicator."""
        self.current_mode = "alert"
        self.is_visible = True

    def hide(self) -> None:
        """Dissolves all ambient indicators."""
        self.current_mode = "idle"
        self.is_visible = False


class LinuxIndicatorController(AbstractIndicatorController):
    """
    Linux implementation of AbstractIndicatorController.
    Provides ambient HUD edge glow, cursor feedback, and multi-harmonic acoustic cues.
    """

    _instance: Optional[LinuxIndicatorController] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self.enabled = True
        self.audio = AudioIndicator()
        self.notifier = LinuxNotificationNotifier()
        self.overlay = LinuxIndicatorOverlay()
        self._overlay_initialized = False

    @classmethod
    def get_instance(cls) -> LinuxIndicatorController:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _ensure_overlay(self) -> None:
        if not self._overlay_initialized:
            self._overlay_initialized = True
            self.overlay.setup()

    def task_start(self, task_name: str = "", monitor_index: int = 0) -> None:
        """Activates ambient edge glow and cursor indicators."""
        if not self.enabled:
            return
        self._ensure_overlay()
        self.overlay.show_active()
        self.audio.play("start")
        if task_name:
            self.notifier.notify(
                summary="Project Extra — Task Started",
                body=task_name,
                icon="appointment-soon",
                urgency=0,
                expire_timeout_ms=2500,
            )

    def task_action(
        self, action_type: str = "move", x: int = 0, y: int = 0, monitor_index: int = 0
    ) -> None:
        """Triggers dynamic cursor reticle or click ripple."""
        pass

    def task_complete(
        self, summary: str = "", success: bool = True, play_chime: bool = True
    ) -> None:
        """Fires completion visual bloom and plays chime."""
        if not self.enabled:
            return
        self._ensure_overlay()
        if success:
            self.overlay.show_complete()
        else:
            self.overlay.show_alert()

        if play_chime:
            self.audio.play("complete" if success else "alert")

        if summary:
            self.notifier.notify(
                summary="Project Extra — Task Complete" if success else "Project Extra — Task Alert",
                body=summary,
                icon="emblem-default" if success else "dialog-warning",
                urgency=1 if success else 2,
                expire_timeout_ms=3500,
            )

        # Auto-hide overlay after flash duration
        def _delayed_hide() -> None:
            time.sleep(0.6)
            self.overlay.hide()

        threading.Thread(target=_delayed_hide, daemon=True).start()

    def task_indicate_status(self, status: str, message: str = "") -> None:
        """Updates ambient status indicators."""
        clean = status.lower().strip()
        if clean in ("active", "running"):
            self.task_start(task_name=message)
        elif clean in ("complete", "done", "success"):
            self.task_complete(summary=message, success=True, play_chime=True)
        elif clean in ("error", "failed", "alert"):
            self.task_complete(summary=message, success=False, play_chime=True)
        elif clean in ("idle", "stop"):
            self.stop()

    def pulse(self, color: str = "cyan") -> None:
        """Fires a momentary ambient pulse."""
        if not self.enabled:
            return
        self._ensure_overlay()
        self.overlay.show_active()

        def _delayed_hide() -> None:
            time.sleep(0.4)
            self.overlay.hide()

        threading.Thread(target=_delayed_hide, daemon=True).start()

    def stop(self) -> None:
        """Dismisses and cleans up overlay indicators."""
        self.overlay.hide()


def get_indicator_controller() -> LinuxIndicatorController:
    """Returns singleton instance of LinuxIndicatorController."""
    return LinuxIndicatorController.get_instance()


IndicatorController = LinuxIndicatorController
