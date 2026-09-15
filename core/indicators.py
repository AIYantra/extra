"""
Project Extra — Task Indication & Human-Agent Awareness Subsystem
Provides non-intrusive, zero-latency feedback during autonomous computer use:
1. Ambient Screen Edge Pulse (Visual): Tells peripheral vision the computer is in autonomous use.
   Flashes soft emerald green on completion.
2. Audio Chime (Auditory): High-fidelity synthesized acoustic chime on completion so the user
   knows the moment the task finishes even when away from the screen.
3. Cursor Halo / Beacon (Tactile): Non-invasive glowing ring around the pointer during movement
   with an animated ripple on click actions.

Engineered with:
- WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_TOPMOST | WS_EX_NOACTIVATE (100% click-through, zero focus stealing)
- SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE) so AI vision models see clean desktop screenshots
  without hallucinating borders or beacons.
"""

from __future__ import annotations

import atexit
import io
import logging
import math
import queue
import struct
import threading
import time
import wave
import winsound
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import win32con
import win32gui
import ctypes
from ctypes import wintypes

from extra.core.geometry import (
    ensure_dpi_aware,
    get_cursor_position,
    get_monitors_info,
    get_primary_monitor,
)

logger = logging.getLogger("extra.indicators")

user32 = ctypes.windll.user32
WDA_EXCLUDEFROMCAPTURE = 0x00000011


class AudioIndicator:
    """
    Synthesizes and plays clean, pleasant acoustic chimes without external audio assets.
    Uses multi-harmonic sine waves with exponential decay envelopes.
    """

    def __init__(self) -> None:
        self.enabled = True
        self._cache: Dict[str, bytes] = {}

    def _synthesize(self, profile: str) -> bytes:
        if profile in self._cache:
            return self._cache[profile]

        sample_rate = 44100
        if profile == "complete":
            # Ascending two-tone chime: E6 (1318.5 Hz) -> B6 (1975.5 Hz)
            tones = [(1318.51, 0.10), (1975.53, 0.35)]
        elif profile == "start":
            # Soft modern confirmation blip: A5 (880 Hz)
            tones = [(880.0, 0.08)]
        elif profile == "attention":
            # Gentle descending chord: G5 (783.99 Hz) -> Eb5 (622.25 Hz)
            tones = [(783.99, 0.12), (622.25, 0.28)]
        else:
            tones = [(1000.0, 0.10)]

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            frames = []
            for freq, duration in tones:
                n_samples = int(duration * sample_rate)
                for i in range(n_samples):
                    t = i / sample_rate
                    attack = min(1.0, t / 0.008)
                    decay = math.exp(-4.5 * t / duration)
                    env = attack * decay
                    # Warm harmonics: fundamental (70%) + 2nd harmonic (22%) + 3rd (8%)
                    val = (
                        0.70 * math.sin(2 * math.pi * freq * t)
                        + 0.22 * math.sin(4 * math.pi * freq * t)
                        + 0.08 * math.sin(6 * math.pi * freq * t)
                    )
                    sample = int(val * env * 28000)
                    frames.append(struct.pack("<h", max(-32767, min(32767, sample))))
            wf.writeframes(b"".join(frames))

        wav_bytes = buf.getvalue()
        self._cache[profile] = wav_bytes
        return wav_bytes

    def play(self, profile: str = "complete") -> None:
        """Plays the designated sound profile asynchronously in a worker thread."""
        if not self.enabled:
            return

        try:
            wav_data = self._synthesize(profile)
            threading.Thread(
                target=lambda: winsound.PlaySound(wav_data, winsound.SND_MEMORY),
                daemon=True,
                name=f"ExtraAudioChime-{profile}",
            ).start()
        except Exception as ex:
            logger.debug("AudioIndicator playback skipped: %s", ex)


class IndicatorWorkerThread(threading.Thread):
    """
    Dedicated Win32 UI thread managing transparent layered overlay windows:
    1. Screen Perimeter Edge Window (Active pulse & completion flash)
    2. Cursor Halo Window (Movement beacon & click ripple)
    """

    COLOR_KEY = 0x000000  # Black transparent chroma key
    # BGR Colors for Win32 GDI
    COLOR_ACTIVE_BORDER = 0xF16663   # Electric Indigo / Violet (RGB: 99, 102, 241)
    COLOR_COMPLETE_BORDER = 0x5EC522 # Emerald Green (RGB: 34, 197, 94)
    COLOR_HALO_DEFAULT = 0xF16663    # Electric Indigo
    COLOR_HALO_RIPPLE = 0x5EC522     # Emerald Green accent on click

    def __init__(self, command_queue: queue.Queue) -> None:
        super().__init__(daemon=True, name="ExtraIndicatorWorker")
        self.cmd_queue = command_queue
        self.running = True

        # State tracking
        self.state = "IDLE"  # IDLE, ACTIVE, COMPLETING
        self.state_start = 0.0
        self.last_action_time = 0.0
        self.auto_timeout_seconds = 12.0

        # Multi-monitor bounds
        self.current_monitor_idx = 0
        self.mon_left = 0
        self.mon_top = 0
        self.mon_w = 1920
        self.mon_h = 1080

        # Window handles
        self.hwnd_edge = 0
        self.hwnd_halo = 0
        self.halo_size = 80
        self.current_edge_color = 0

        # Ripple tracking
        self.ripple_active = False
        self.ripple_start = 0.0

    def _setup_windows(self) -> None:
        ensure_dpi_aware()
        prim = get_primary_monitor()
        self.mon_left = prim.left
        self.mon_top = prim.top
        self.mon_w = prim.width
        self.mon_h = prim.height

        # 1. Register Edge Class
        wc_edge = win32gui.WNDCLASS()
        wc_edge.lpszClassName = "ExtraEdgeOverlayClass"
        wc_edge.lpfnWndProc = win32gui.DefWindowProc
        try:
            win32gui.RegisterClass(wc_edge)
        except Exception:
            pass

        # 2. Register Halo Class
        wc_halo = win32gui.WNDCLASS()
        wc_halo.lpszClassName = "ExtraHaloOverlayClass"
        wc_halo.lpfnWndProc = win32gui.DefWindowProc
        try:
            win32gui.RegisterClass(wc_halo)
        except Exception:
            pass

        ex_style = (
            win32con.WS_EX_TOPMOST
            | win32con.WS_EX_TRANSPARENT
            | win32con.WS_EX_LAYERED
            | win32con.WS_EX_TOOLWINDOW
            | win32con.WS_EX_NOACTIVATE
        )

        # Create Edge Window
        self.hwnd_edge = win32gui.CreateWindowEx(
            ex_style,
            "ExtraEdgeOverlayClass",
            "ExtraEdgeOverlay",
            win32con.WS_POPUP,
            self.mon_left,
            self.mon_top,
            self.mon_w,
            self.mon_h,
            0,
            0,
            0,
            None,
        )

        # Create Cursor Halo Window
        self.hwnd_halo = win32gui.CreateWindowEx(
            ex_style,
            "ExtraHaloOverlayClass",
            "ExtraHaloOverlay",
            win32con.WS_POPUP,
            0,
            0,
            self.halo_size,
            self.halo_size,
            0,
            0,
            0,
            None,
        )

        # Exclude from DWM / DXGI / PrintWindow screenshot captures
        for hwnd in (self.hwnd_edge, self.hwnd_halo):
            try:
                user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
            except Exception:
                pass

        # Initialize transparency
        win32gui.SetLayeredWindowAttributes(
            self.hwnd_edge,
            self.COLOR_KEY,
            0,
            win32con.LWA_COLORKEY | win32con.LWA_ALPHA,
        )
        win32gui.SetLayeredWindowAttributes(
            self.hwnd_halo,
            self.COLOR_KEY,
            0,
            win32con.LWA_COLORKEY | win32con.LWA_ALPHA,
        )

    def _update_monitor_bounds(self, monitor_index: int) -> None:
        if monitor_index == self.current_monitor_idx and self.mon_w > 0:
            return

        monitors = get_monitors_info()
        for m in monitors:
            if m.index == monitor_index:
                self.current_monitor_idx = monitor_index
                self.mon_left = m.left
                self.mon_top = m.top
                self.mon_w = m.width
                self.mon_h = m.height
                win32gui.SetWindowPos(
                    self.hwnd_edge,
                    win32con.HWND_TOPMOST,
                    self.mon_left,
                    self.mon_top,
                    self.mon_w,
                    self.mon_h,
                    win32con.SWP_NOACTIVATE,
                )
                self.current_edge_color = 0  # Trigger border redraw
                break

    def _draw_edge(self, color_bgr: int, thickness: int = 4) -> None:
        if not self.hwnd_edge:
            return

        hdc = win32gui.GetDC(self.hwnd_edge)
        memdc = win32gui.CreateCompatibleDC(hdc)
        bmp = win32gui.CreateCompatibleBitmap(hdc, self.mon_w, self.mon_h)
        win32gui.SelectObject(memdc, bmp)

        # Fill background with Chroma Key
        black_brush = win32gui.CreateSolidBrush(self.COLOR_KEY)
        win32gui.FillRect(memdc, (0, 0, self.mon_w, self.mon_h), black_brush)

        # Draw Perimeter Borders
        border_brush = win32gui.CreateSolidBrush(color_bgr)
        win32gui.FillRect(memdc, (0, 0, self.mon_w, thickness), border_brush)
        win32gui.FillRect(memdc, (0, self.mon_h - thickness, self.mon_w, self.mon_h), border_brush)
        win32gui.FillRect(memdc, (0, 0, thickness, self.mon_h), border_brush)
        win32gui.FillRect(memdc, (self.mon_w - thickness, 0, self.mon_w, self.mon_h), border_brush)

        # Push to window
        win32gui.BitBlt(hdc, 0, 0, self.mon_w, self.mon_h, memdc, 0, 0, win32con.SRCCOPY)

        # Cleanup GDI handles
        win32gui.DeleteObject(border_brush)
        win32gui.DeleteObject(black_brush)
        win32gui.DeleteObject(bmp)
        win32gui.DeleteDC(memdc)
        win32gui.ReleaseDC(self.hwnd_edge, hdc)
        self.current_edge_color = color_bgr

    def _draw_halo(self, radius: int, thickness: int = 2, color_bgr: int = 0xF16663) -> None:
        if not self.hwnd_halo:
            return

        half = self.halo_size // 2
        hdc = win32gui.GetDC(self.hwnd_halo)
        memdc = win32gui.CreateCompatibleDC(hdc)
        bmp = win32gui.CreateCompatibleBitmap(hdc, self.halo_size, self.halo_size)
        win32gui.SelectObject(memdc, bmp)

        # Clear background
        black_brush = win32gui.CreateSolidBrush(self.COLOR_KEY)
        win32gui.FillRect(memdc, (0, 0, self.halo_size, self.halo_size), black_brush)

        # Outer ring
        pen = win32gui.CreatePen(win32con.PS_SOLID, thickness, color_bgr)
        null_brush = win32gui.GetStockObject(win32con.NULL_BRUSH)
        win32gui.SelectObject(memdc, pen)
        win32gui.SelectObject(memdc, null_brush)
        win32gui.Ellipse(memdc, half - radius, half - radius, half + radius, half + radius)

        # Center target dot
        dot_brush = win32gui.CreateSolidBrush(0xFFFFFF)
        dot_pen = win32gui.CreatePen(win32con.PS_SOLID, 1, 0xFFFFFF)
        win32gui.SelectObject(memdc, dot_brush)
        win32gui.SelectObject(memdc, dot_pen)
        win32gui.Ellipse(memdc, half - 3, half - 3, half + 3, half + 3)

        # Push to window
        win32gui.BitBlt(hdc, 0, 0, self.halo_size, self.halo_size, memdc, 0, 0, win32con.SRCCOPY)

        # Cleanup
        win32gui.DeleteObject(dot_brush)
        win32gui.DeleteObject(dot_pen)
        win32gui.DeleteObject(pen)
        win32gui.DeleteObject(black_brush)
        win32gui.DeleteObject(bmp)
        win32gui.DeleteDC(memdc)
        win32gui.ReleaseDC(self.hwnd_halo, hdc)

    def _set_halo_pos(self, x: int, y: int) -> None:
        half = self.halo_size // 2
        win32gui.SetWindowPos(
            self.hwnd_halo,
            win32con.HWND_TOPMOST,
            x - half,
            y - half,
            0,
            0,
            win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE,
        )

    def run(self) -> None:
        self._setup_windows()

        while self.running:
            # 1. Process all pending queue commands
            try:
                while True:
                    cmd, data = self.cmd_queue.get_nowait()
                    if cmd == "START":
                        self.state = "ACTIVE"
                        self.state_start = time.time()
                        self.last_action_time = time.time()
                        mon_idx = data.get("monitor_index", 0)
                        self._update_monitor_bounds(mon_idx)
                        win32gui.ShowWindow(self.hwnd_edge, win32con.SW_SHOWNOACTIVATE)
                        win32gui.ShowWindow(self.hwnd_halo, win32con.SW_SHOWNOACTIVATE)
                        # Position halo at current cursor
                        cur_x, cur_y = get_cursor_position()
                        self._set_halo_pos(cur_x, cur_y)

                    elif cmd == "ACTION":
                        self.last_action_time = time.time()
                        mon_idx = data.get("monitor_index", 0)
                        self._update_monitor_bounds(mon_idx)

                        if self.state != "ACTIVE":
                            self.state = "ACTIVE"
                            self.state_start = time.time()
                            win32gui.ShowWindow(self.hwnd_edge, win32con.SW_SHOWNOACTIVATE)
                            win32gui.ShowWindow(self.hwnd_halo, win32con.SW_SHOWNOACTIVATE)

                        x = data.get("x")
                        y = data.get("y")
                        if x is not None and y is not None:
                            self._set_halo_pos(x, y)

                        action_type = data.get("action", "move")
                        if action_type == "click":
                            self.ripple_active = True
                            self.ripple_start = time.time()

                    elif cmd == "COMPLETE":
                        self.state = "COMPLETING"
                        self.state_start = time.time()

                    elif cmd == "STOP":
                        self.state = "IDLE"

                    elif cmd == "SHUTDOWN":
                        self.running = False
                        break
            except queue.Empty:
                pass

            # 2. Pump Win32 messages
            win32gui.PumpWaitingMessages()

            # 3. Animation state machine
            now = time.time()
            if self.state == "ACTIVE":
                if self.current_edge_color != self.COLOR_ACTIVE_BORDER:
                    self._draw_edge(self.COLOR_ACTIVE_BORDER, thickness=4)

                # Breathing alpha pulse: oscillates between 110 and 220
                elapsed = now - self.state_start
                alpha = int(140 + 80 * math.sin(elapsed * 5.0))
                win32gui.SetLayeredWindowAttributes(
                    self.hwnd_edge,
                    self.COLOR_KEY,
                    alpha,
                    win32con.LWA_COLORKEY | win32con.LWA_ALPHA,
                )

                # Animate halo
                if self.ripple_active:
                    r_elapsed = now - self.ripple_start
                    duration = 0.22
                    if r_elapsed < duration:
                        progress = r_elapsed / duration
                        r = int(16 + progress * 20)
                        h_alpha = max(20, int(240 * (1.0 - progress * 0.8)))
                        self._draw_halo(
                            r,
                            thickness=max(1, int(3 * (1.0 - progress))),
                            color_bgr=self.COLOR_HALO_RIPPLE,
                        )
                        win32gui.SetLayeredWindowAttributes(
                            self.hwnd_halo,
                            self.COLOR_KEY,
                            h_alpha,
                            win32con.LWA_COLORKEY | win32con.LWA_ALPHA,
                        )
                    else:
                        self.ripple_active = False
                        self._draw_halo(16, thickness=2, color_bgr=self.COLOR_HALO_DEFAULT)
                        win32gui.SetLayeredWindowAttributes(
                            self.hwnd_halo,
                            self.COLOR_KEY,
                            210,
                            win32con.LWA_COLORKEY | win32con.LWA_ALPHA,
                        )
                else:
                    self._draw_halo(16, thickness=2, color_bgr=self.COLOR_HALO_DEFAULT)
                    win32gui.SetLayeredWindowAttributes(
                        self.hwnd_halo,
                        self.COLOR_KEY,
                        210,
                        win32con.LWA_COLORKEY | win32con.LWA_ALPHA,
                    )

                # Auto-idle timeout
                if now - self.last_action_time > self.auto_timeout_seconds:
                    self.state = "IDLE"

            elif self.state == "COMPLETING":
                elapsed = now - self.state_start
                if self.current_edge_color != self.COLOR_COMPLETE_BORDER:
                    self._draw_edge(self.COLOR_COMPLETE_BORDER, thickness=5)
                    # Hide halo on complete
                    win32gui.ShowWindow(self.hwnd_halo, win32con.SW_HIDE)

                if elapsed < 1.0:
                    # Flash vibrant emerald green
                    win32gui.SetLayeredWindowAttributes(
                        self.hwnd_edge,
                        self.COLOR_KEY,
                        245,
                        win32con.LWA_COLORKEY | win32con.LWA_ALPHA,
                    )
                elif elapsed < 1.6:
                    # Smooth dissolution
                    fade_progress = (elapsed - 1.0) / 0.6
                    alpha = max(0, int(245 * (1.0 - fade_progress)))
                    win32gui.SetLayeredWindowAttributes(
                        self.hwnd_edge,
                        self.COLOR_KEY,
                        alpha,
                        win32con.LWA_COLORKEY | win32con.LWA_ALPHA,
                    )
                else:
                    self.state = "IDLE"

            elif self.state == "IDLE":
                win32gui.ShowWindow(self.hwnd_edge, win32con.SW_HIDE)
                win32gui.ShowWindow(self.hwnd_halo, win32con.SW_HIDE)
                self.current_edge_color = 0
                time.sleep(0.04)

            time.sleep(0.025)

        # Cleanup on thread exit
        if self.hwnd_edge:
            win32gui.DestroyWindow(self.hwnd_edge)
        if self.hwnd_halo:
            win32gui.DestroyWindow(self.hwnd_halo)


class IndicatorController:
    """
    Singleton Controller for Task Indications across Extra.
    Coordinates ambient visual pulse, audio chime, and cursor halo.
    """

    _instance: Optional[IndicatorController] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self.enabled = True
        self.audio = AudioIndicator()
        self.cmd_queue: queue.Queue = queue.Queue()
        self._worker: Optional[IndicatorWorkerThread] = None
        self._ensure_worker()
        atexit.register(self.shutdown)

    @classmethod
    def get_instance(cls) -> IndicatorController:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _ensure_worker(self) -> None:
        if self._worker is None or not self._worker.is_alive():
            self._worker = IndicatorWorkerThread(self.cmd_queue)
            self._worker.start()

    def set_enabled(self, enabled: bool) -> None:
        """Enables or disables visual indicators."""
        self.enabled = enabled
        if not enabled:
            self.task_stop()

    def set_audio_enabled(self, enabled: bool) -> None:
        """Enables or disables audio chime feedback."""
        self.audio.enabled = enabled

    def task_start(self, task_name: Optional[str] = None, monitor_index: int = 0) -> None:
        """
        Activates the ambient screen edge pulse and cursor beacon.
        Optionally plays a subtle confirmation blip.
        """
        if not self.enabled:
            return
        self._ensure_worker()
        self.cmd_queue.put(("START", {"task_name": task_name, "monitor_index": monitor_index}))
        logger.info("Indicator: Task started ('%s')", task_name or "Autonomous")

    def task_action(
        self,
        action: str = "move",
        x: Optional[int] = None,
        y: Optional[int] = None,
        monitor_index: int = 0,
    ) -> None:
        """
        Notifies of an input action (click, move, type, drag).
        Refreshes ambient active mode and updates cursor halo coordinates.
        """
        if not self.enabled:
            return
        self._ensure_worker()
        self.cmd_queue.put(
            (
                "ACTION",
                {
                    "action": action,
                    "x": x,
                    "y": y,
                    "monitor_index": monitor_index,
                },
            )
        )

    def task_complete(
        self,
        summary: Optional[str] = None,
        success: bool = True,
        play_chime: bool = True,
    ) -> None:
        """
        Triggers the task completion sequence:
        1. Screen perimeter flashes soft emerald green for ~1.5s then dissolves.
        2. Plays crisp multi-harmonic completion audio chime.
        3. Fades and dismisses cursor beacon.
        """
        if not self.enabled:
            return
        self._ensure_worker()
        self.cmd_queue.put(("COMPLETE", {"summary": summary, "success": success}))
        if play_chime:
            self.audio.play("complete" if success else "attention")
        logger.info("Indicator: Task completed (%s)", summary or "Success")

    def task_stop(self) -> None:
        """Immediately hides and resets all indicators."""
        if self._worker and self._worker.is_alive():
            self.cmd_queue.put(("STOP", {}))

    def shutdown(self) -> None:
        """Gracefully shuts down indicator windows and background thread."""
        if self._worker and self._worker.is_alive():
            self.cmd_queue.put(("SHUTDOWN", {}))
            self._worker.join(timeout=0.5)


# Global convenience accessor
def get_indicator_controller() -> IndicatorController:
    return IndicatorController.get_instance()
