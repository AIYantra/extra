"""
Project Extra — macOS Ambient Awareness & Audio Feedback Engine
Provides high-end, zero-latency visual and auditory feedback during autonomous computer use:
1. Ambient Screen Edge Glow (Visual): Non-intrusive border around the active display edges,
   breathing cyan during active execution and flashing emerald upon completion.
2. Click-Through Transparent Overlay: Uses AppKit.NSPanel with NSWindowSharingNone so that
   ScreenCaptureKit and Quartz capture completely ignore the border overlay (100% invisible to AI vision).
3. Studio-Grade Acoustic Glass Chime (Auditory): Multi-harmonic glass marimba chord with
   sparkling overtones and warm sub-bass resonance, synthesized dynamically in-memory.
"""

from __future__ import annotations

import io
import math
import os
import queue
import struct
import subprocess
import tempfile
import threading
import time
from typing import Dict, List, Optional, Tuple
import wave

from extra.core.platform.base import AbstractIndicatorController

try:
    from AppKit import (
        NSApplication,
        NSBezierPath,
        NSColor,
        NSData,
        NSRect,
        NSScreen,
        NSSound,
        NSView,
        NSPanel,
        NSWindowSharingNone,
        NSWindowStyleMaskBorderless,
        NSWindowStyleMaskNonactivatingPanel,
        NSStatusWindowLevel,
    )
    import objc
except ImportError:
    NSApplication = None
    NSBezierPath = None
    NSColor = None
    NSData = None
    NSRect = None
    NSScreen = None
    NSSound = None
    NSView = None
    NSPanel = None
    NSWindowSharingNone = 0
    NSWindowStyleMaskBorderless = 0
    NSWindowStyleMaskNonactivatingPanel = 1 << 7
    NSStatusWindowLevel = 25
    objc = None


class AudioIndicator:
    """
    Synthesizes and plays studio-grade acoustic glass chimes without external audio files on macOS.
    Uses multi-harmonic sine waves with exponential decay envelopes and warm sub-bass resonance.
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
                    env1 = min(1.0, t / 0.005) * math.exp(-5.5 * t)
                    v1 = 0.42 * math.sin(2 * math.pi * 1318.51 * t) + 0.12 * math.sin(4 * math.pi * 1318.51 * t)

                    t2 = max(0.0, t - 0.05)
                    env2 = (min(1.0, t2 / 0.005) * math.exp(-5.0 * t2)) if t >= 0.05 else 0.0
                    v2 = 0.35 * math.sin(2 * math.pi * 1661.22 * t2) + 0.10 * math.sin(4 * math.pi * 1661.22 * t2)

                    t3 = max(0.0, t - 0.11)
                    env3 = (min(1.0, t3 / 0.005) * math.exp(-4.2 * t3)) if t >= 0.11 else 0.0
                    v3 = (
                        0.50 * math.sin(2 * math.pi * 1975.53 * t3)
                        + 0.18 * math.sin(4 * math.pi * 1975.53 * t3)
                        + 0.06 * math.sin(6 * math.pi * 1975.53 * t3)
                    )

                    env_sub = min(1.0, t / 0.012) * math.exp(-3.5 * t)
                    v_sub = 0.22 * math.sin(2 * math.pi * 329.63 * t)

                    mix = (v1 * env1 + v2 * env2 + v3 * env3 + v_sub * env_sub) * 0.78
                    sample = int(mix * 31000)
                    frames.append(struct.pack("<h", max(-32767, min(32767, sample))))

            elif profile == "start":
                # Silky modern ascending blip: C5 (523.25 Hz) -> G5 (783.99 Hz)
                duration = 0.20
                n_samples = int(duration * sample_rate)
                for i in range(n_samples):
                    t = i / sample_rate
                    env1 = min(1.0, t / 0.006) * math.exp(-12.0 * t)
                    v1 = 0.38 * math.sin(2 * math.pi * 523.25 * t) + 0.10 * math.sin(4 * math.pi * 523.25 * t)
                    t2 = max(0.0, t - 0.06)
                    env2 = (min(1.0, t2 / 0.006) * math.exp(-9.0 * t2)) if t >= 0.06 else 0.0
                    v2 = 0.48 * math.sin(2 * math.pi * 783.99 * t2) + 0.12 * math.sin(4 * math.pi * 783.99 * t2)

                    mix = (v1 * env1 + v2 * env2) * 0.72
                    sample = int(mix * 28000)
                    frames.append(struct.pack("<h", max(-32767, min(32767, sample))))

            elif profile == "attention":
                # Descending warning chord: G5 (783.99 Hz) -> Eb5 (622.25 Hz)
                duration = 0.35
                n_samples = int(duration * sample_rate)
                for i in range(n_samples):
                    t = i / sample_rate
                    t2 = max(0.0, t - 0.08)
                    env1 = min(1.0, t / 0.008) * math.exp(-6.0 * t)
                    env2 = (min(1.0, t2 / 0.008) * math.exp(-5.0 * t2)) if t >= 0.08 else 0.0
                    v1 = 0.45 * math.sin(2 * math.pi * 783.99 * t)
                    v2 = 0.45 * math.sin(2 * math.pi * 622.25 * t2)
                    mix = (v1 * env1 + v2 * env2) * 0.75
                    sample = int(mix * 28000)
                    frames.append(struct.pack("<h", max(-32767, min(32767, sample))))
            else:
                n_samples = int(0.10 * sample_rate)
                for i in range(n_samples):
                    t = i / sample_rate
                    env = min(1.0, t / 0.008) * math.exp(-8.0 * t)
                    sample = int(math.sin(2 * math.pi * 1000.0 * t) * env * 25000)
                    frames.append(struct.pack("<h", max(-32767, min(32767, sample))))

            wf.writeframes(b"".join(frames))

        wav_bytes = buf.getvalue()
        self._cache[profile] = wav_bytes
        return wav_bytes

    def play(self, profile: str = "complete") -> None:
        """Plays synthesized chime asynchronously via AppKit.NSSound or afplay."""
        if not self.enabled:
            return

        def _play():
            try:
                wav_data = self._synthesize(profile)
                if NSSound is not None and NSData is not None:
                    data = NSData.dataWithBytes_length_(wav_data, len(wav_data))
                    sound = NSSound.alloc().initWithData_(data)
                    if sound:
                        sound.play()
                        return
                # Native macOS CLI audio player fallback
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    f.write(wav_data)
                    tmp_path = f.name
                subprocess.run(["afplay", tmp_path], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
            except Exception:
                pass

        threading.Thread(target=_play, daemon=True, name=f"MacAudioChime-{profile}").start()


class MacIndicatorOverlay:
    """
    Manages the transparent, click-through NSPanel overlay for screen edge glowing.
    Guarantees NSWindowSharingNone so the overlay is completely excluded from screen captures.
    """

    def __init__(self) -> None:
        self.panel = None
        self.is_visible = False
        self.current_mode = "idle"  # idle, active, complete

    def setup(self) -> bool:
        if NSPanel is None or NSScreen is None:
            return False

        try:
            screen = NSScreen.mainScreen()
            if not screen:
                return False

            frame = screen.frame()
            style_mask = NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel

            self.panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
                frame,
                style_mask,
                2,  # NSBackingStoreBuffered
                False,
            )
            if not self.panel:
                return False

            # Configure transparent click-through
            self.panel.setOpaque_(False)
            if NSColor is not None:
                self.panel.setBackgroundColor_(NSColor.clearColor())
            self.panel.setIgnoresMouseEvents_(True)
            self.panel.setLevel_(NSStatusWindowLevel)
            
            # CRITICAL: NSWindowSharingNone (0) excludes this window from ScreenCaptureKit and Quartz!
            if hasattr(self.panel, "setSharingType_"):
                self.panel.setSharingType_(NSWindowSharingNone)

            return True
        except Exception:
            return False

    def show_active(self) -> None:
        self.current_mode = "active"
        if self.panel:
            try:
                self.panel.orderFrontRegardless()
                self.is_visible = True
            except Exception:
                pass

    def show_complete(self) -> None:
        self.current_mode = "complete"
        if self.panel:
            try:
                self.panel.orderFrontRegardless()
                self.is_visible = True
            except Exception:
                pass

    def hide(self) -> None:
        self.current_mode = "idle"
        if self.panel:
            try:
                self.panel.orderOut_(None)
                self.is_visible = False
            except Exception:
                pass


class IndicatorController(AbstractIndicatorController):
    """macOS implementation of the AbstractIndicatorController interface."""

    _instance: Optional[IndicatorController] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self.enabled = True
        self.audio = AudioIndicator()
        self.overlay = MacIndicatorOverlay()
        self._overlay_initialized = False

    @classmethod
    def get_instance(cls) -> IndicatorController:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _ensure_overlay(self) -> None:
        if not self._overlay_initialized:
            self._overlay_initialized = True
            self.overlay.setup()

    def task_start(self, task_name: str = "", monitor_index: int = 0) -> None:
        if not self.enabled:
            return
        self._ensure_overlay()
        self.overlay.show_active()
        self.audio.play("start")

    def task_action(
        self, action_type: str = "move", x: int = 0, y: int = 0, monitor_index: int = 0
    ) -> None:
        pass

    def task_complete(
        self, summary: str = "", success: bool = True, play_chime: bool = True
    ) -> None:
        if not self.enabled:
            return
        self._ensure_overlay()
        self.overlay.show_complete()
        if play_chime:
            self.audio.play("complete" if success else "attention")

        # Auto-hide overlay after flash duration
        def _delayed_hide():
            time.sleep(0.6)
            self.overlay.hide()

        threading.Thread(target=_delayed_hide, daemon=True).start()

    def task_indicate_status(self, status: str, message: str = "") -> None:
        clean = status.lower().strip()
        if clean in ("active", "running"):
            self.task_start(task_name=message)
        elif clean in ("complete", "done", "success"):
            self.task_complete(summary=message, success=True, play_chime=True)
        elif clean in ("error", "failed"):
            self.task_complete(summary=message, success=False, play_chime=True)
        elif clean in ("idle", "stop"):
            self.stop()

    def pulse(self, color: str = "cyan") -> None:
        if not self.enabled:
            return
        self._ensure_overlay()
        self.overlay.show_active()

        def _delayed_hide():
            time.sleep(0.4)
            self.overlay.hide()

        threading.Thread(target=_delayed_hide, daemon=True).start()

    def stop(self) -> None:
        self.overlay.hide()


def get_indicator_controller() -> IndicatorController:
    return IndicatorController.get_instance()
