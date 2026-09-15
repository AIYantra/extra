"""
Project Extra — Task Indication & Human-Agent Awareness Subsystem (V2 Polish)
Provides high-end, zero-latency feedback during autonomous computer use:
1. Ambient Screen Edge Glow (Visual): Multi-layered cascading neon bloom around the screen bezels
   with organic chromatic breathing while active, erupting into a vibrant emerald-mint aurora on completion.
2. Luxury Harmonic Audio Chime (Auditory): Multi-timbre glass marimba chord with sparkling overtones
   and acoustic sub-bass resonance, informing the user the moment a task starts or finishes.
3. Tactical Cursor Reticle & Shockwave (Tactile): High-precision targeting reticle with 4-point crosshairs
   and animated dual-shockwave ripples on click actions.

Engineered with:
- WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_TOPMOST | WS_EX_NOACTIVATE (100% click-through, zero focus stealing)
- SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE) so AI vision models see clean desktop screenshots
  without hallucinating glowing borders or reticles.
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
    Synthesizes and plays studio-grade acoustic glass chimes without external audio files.
    Uses multi-harmonic sine waves with exponential decay envelopes and sub-bass body resonance.
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

                    mix = (v1 * env1 + v2 * env2 + v3 * env3 + v_sub * env_sub) * 0.78
                    sample = int(mix * 31000)
                    frames.append(struct.pack("<h", max(-32767, min(32767, sample))))

            elif profile == "start":
                # Silky modern ascending blip: C5 (523.25 Hz) -> G5 (783.99 Hz)
                duration = 0.20
                n_samples = int(duration * sample_rate)
                for i in range(n_samples):
                    t = i / sample_rate
                    # Tone 1 at 0.0s
                    env1 = min(1.0, t / 0.006) * math.exp(-12.0 * t)
                    v1 = 0.38 * math.sin(2 * math.pi * 523.25 * t) + 0.10 * math.sin(4 * math.pi * 523.25 * t)
                    # Tone 2 at 0.06s
                    t2 = max(0.0, t - 0.06)
                    env2 = (min(1.0, t2 / 0.006) * math.exp(-9.0 * t2)) if t >= 0.06 else 0.0
                    v2 = 0.48 * math.sin(2 * math.pi * 783.99 * t2) + 0.12 * math.sin(4 * math.pi * 783.99 * t2)

                    mix = (v1 * env1 + v2 * env2) * 0.72
                    sample = int(mix * 28000)
                    frames.append(struct.pack("<h", max(-32767, min(32767, sample))))

            elif profile == "attention":
                # Warm descending attention chord: G5 (783.99 Hz) -> Eb5 (622.25 Hz)
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
                tones = [(1000.0, 0.10)]
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
        """Plays designated acoustic sound profile asynchronously without blocking execution."""
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
    Dedicated Win32 UI thread managing multi-layered transparent layered overlay windows:
    1. Cascading Ambient Neon Glow (Breathing Aurora pulse & emerald flash)
    2. Tactical Targeting Reticle (Precision crosshairs & expanding shockwaves)
    """

    COLOR_KEY = 0x000000  # Black transparent chroma key

    # Aurora Palette (BGR Format for Win32 GDI)
    # Active: Electric Cyan, Vibrant Indigo, Neon Violet, Deep Velvet
    ACTIVE_BLOOM_BANDS = [
        (0xD4B606, 0, 2),  # Band 0: Crisp Cyber Cyan (RGB: 6, 182, 212)
        (0xF16663, 2, 2),  # Band 1: Electric Indigo (RGB: 99, 102, 241)
        (0xF755A8, 4, 3),  # Band 2: Neon Violet Bloom (RGB: 168, 85, 247)
        (0x951D4C, 7, 4),  # Band 3: Deep Velvet Aura (RGB: 76, 29, 149)
    ]

    # Completion: Sparkling Mint, Vivid Emerald, Deep Jade, Forest Aurora
    COMPLETE_BLOOM_BANDS = [
        (0xD0F3A7, 0, 2),  # Band 0: Sparkling Mint (RGB: 167, 243, 208)
        (0x81B910, 2, 3),  # Band 1: Vivid Emerald (RGB: 16, 185, 129)
        (0x699605, 5, 4),  # Band 2: Deep Jade (RGB: 5, 150, 105)
        (0x577804, 9, 5),  # Band 3: Forest Aurora (RGB: 4, 120, 87)
    ]

    COLOR_RETICLE_CORE = 0xF16663     # Electric Indigo
    COLOR_RETICLE_ACCENT = 0xD4B606   # Cyber Cyan
    COLOR_RETICLE_SHOCK = 0x5EC522    # Emerald Mint shockwave

    def __init__(self, command_queue: queue.Queue) -> None:
        super().__init__(daemon=True, name="ExtraIndicatorWorker")
        self.cmd_queue = command_queue
        self.running = True

        # State tracking
        self.state = "IDLE"  # IDLE, ACTIVE, COMPLETING
        self.state_start = 0.0
        self.last_action_time = 0.0
        self.auto_timeout_seconds = 14.0

        # Multi-monitor bounds
        self.current_monitor_idx = 0
        self.mon_left = 0
        self.mon_top = 0
        self.mon_w = 1920
        self.mon_h = 1080

        # Window handles
        self.hwnd_edge = 0
        self.hwnd_halo = 0
        self.halo_size = 96  # High-resolution reticle canvas
        self.current_edge_mode = ""

        # Shockwave animation tracking
        self.shockwave_active = False
        self.shockwave_start = 0.0

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

        # Create Cursor Reticle Window
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
                self.current_edge_mode = ""  # Trigger border redraw
                break

    def _draw_edge_bloom(self, bands: List[Tuple[int, int, int]]) -> None:
        """Renders multi-layer cascading neon bloom rectangles into screen bezels."""
        if not self.hwnd_edge:
            return

        hdc = win32gui.GetDC(self.hwnd_edge)
        memdc = win32gui.CreateCompatibleDC(hdc)
        bmp = win32gui.CreateCompatibleBitmap(hdc, self.mon_w, self.mon_h)
        win32gui.SelectObject(memdc, bmp)

        # Clear black chroma key
        bk = win32gui.CreateSolidBrush(self.COLOR_KEY)
        win32gui.FillRect(memdc, (0, 0, self.mon_w, self.mon_h), bk)

        # Draw cascading glow bands
        for color_bgr, inset, thickness in bands:
            br = win32gui.CreateSolidBrush(color_bgr)
            # Top
            win32gui.FillRect(memdc, (inset, inset, self.mon_w - inset, inset + thickness), br)
            # Bottom
            win32gui.FillRect(memdc, (inset, self.mon_h - inset - thickness, self.mon_w - inset, self.mon_h - inset), br)
            # Left
            win32gui.FillRect(memdc, (inset, inset, inset + thickness, self.mon_h - inset), br)
            # Right
            win32gui.FillRect(memdc, (self.mon_w - inset - thickness, inset, self.mon_w - inset, self.mon_h - inset), br)
            win32gui.DeleteObject(br)

        win32gui.BitBlt(hdc, 0, 0, self.mon_w, self.mon_h, memdc, 0, 0, win32con.SRCCOPY)

        win32gui.DeleteObject(bk)
        win32gui.DeleteObject(bmp)
        win32gui.DeleteDC(memdc)
        win32gui.ReleaseDC(self.hwnd_edge, hdc)

    def _draw_tactical_reticle(
        self,
        shockwave_radius: Optional[int] = None,
        shockwave_alpha_ratio: float = 1.0,
        flash_center: bool = False,
    ) -> None:
        """Renders high-precision targeting reticle with 4-point crosshairs and shockwave bloom."""
        if not self.hwnd_halo:
            return

        half = self.halo_size // 2
        hdc = win32gui.GetDC(self.hwnd_halo)
        memdc = win32gui.CreateCompatibleDC(hdc)
        bmp = win32gui.CreateCompatibleBitmap(hdc, self.halo_size, self.halo_size)
        win32gui.SelectObject(memdc, bmp)

        # Clear background
        bk = win32gui.CreateSolidBrush(self.COLOR_KEY)
        win32gui.FillRect(memdc, (0, 0, self.halo_size, self.halo_size), bk)

        null_brush = win32gui.GetStockObject(win32con.NULL_BRUSH)
        win32gui.SelectObject(memdc, null_brush)

        # 1. Faint outer guidance aura ring (radius 24)
        pen_aura = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x4C1D95)  # Deep purple
        win32gui.SelectObject(memdc, pen_aura)
        win32gui.Ellipse(memdc, half - 24, half - 24, half + 24, half + 24)

        # 2. Inner crisp reticle ring (radius 15)
        pen_core = win32gui.CreatePen(win32con.PS_SOLID, 2, self.COLOR_RETICLE_CORE)
        win32gui.SelectObject(memdc, pen_core)
        win32gui.Ellipse(memdc, half - 15, half - 15, half + 15, half + 15)

        # 3. Precision 4-point crosshair ticks (12, 3, 6, 9 o'clock)
        pen_ticks = win32gui.CreatePen(win32con.PS_SOLID, 1, 0xFFFFFF)
        win32gui.SelectObject(memdc, pen_ticks)
        # Top tick
        win32gui.MoveToEx(memdc, half, half - 26)
        win32gui.LineTo(memdc, half, half - 17)
        # Bottom tick
        win32gui.MoveToEx(memdc, half, half + 17)
        win32gui.LineTo(memdc, half, half + 26)
        # Left tick
        win32gui.MoveToEx(memdc, half - 26, half)
        win32gui.LineTo(memdc, half - 17, half)
        # Right tick
        win32gui.MoveToEx(memdc, half + 17, half)
        win32gui.LineTo(memdc, half + 26, half)

        # 4. Animated expanding shockwave on click
        if shockwave_radius:
            shock_thickness = max(1, int(3 * shockwave_alpha_ratio))
            pen_shock = win32gui.CreatePen(win32con.PS_SOLID, shock_thickness, self.COLOR_RETICLE_SHOCK)
            win32gui.SelectObject(memdc, pen_shock)
            win32gui.Ellipse(
                memdc,
                half - shockwave_radius,
                half - shockwave_radius,
                half + shockwave_radius,
                half + shockwave_radius,
            )
            # Secondary ambient shockwave ring
            outer_shock = min(half - 2, shockwave_radius + 6)
            pen_outer_shock = win32gui.CreatePen(win32con.PS_SOLID, 1, self.COLOR_RETICLE_ACCENT)
            win32gui.SelectObject(memdc, pen_outer_shock)
            win32gui.Ellipse(memdc, half - outer_shock, half - outer_shock, half + outer_shock, half + outer_shock)
            win32gui.DeleteObject(pen_shock)
            win32gui.DeleteObject(pen_outer_shock)

        # 5. Center laser pip
        pip_color = 0x5EC522 if flash_center else 0xFFFFFF
        dot_brush = win32gui.CreateSolidBrush(pip_color)
        dot_pen = win32gui.CreatePen(win32con.PS_SOLID, 1, pip_color)
        win32gui.SelectObject(memdc, dot_brush)
        win32gui.SelectObject(memdc, dot_pen)
        win32gui.Ellipse(memdc, half - 3, half - 3, half + 3, half + 3)

        # Push to screen
        win32gui.BitBlt(hdc, 0, 0, self.halo_size, self.halo_size, memdc, 0, 0, win32con.SRCCOPY)

        # Cleanup handles
        win32gui.DeleteObject(dot_pen)
        win32gui.DeleteObject(dot_brush)
        win32gui.DeleteObject(pen_ticks)
        win32gui.DeleteObject(pen_core)
        win32gui.DeleteObject(pen_aura)
        win32gui.DeleteObject(bk)
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
            # 1. Process pending queue commands
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
                            self.shockwave_active = True
                            self.shockwave_start = time.time()

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

            # 3. Animation State Machine
            now = time.time()
            if self.state == "ACTIVE":
                if self.current_edge_mode != "ACTIVE":
                    self._draw_edge_bloom(self.ACTIVE_BLOOM_BANDS)
                    self.current_edge_mode = "ACTIVE"

                # Breathing organic pulse: oscillates between alpha 125 and 230
                elapsed = now - self.state_start
                alpha = int(145 + 85 * math.sin(elapsed * 4.0))
                win32gui.SetLayeredWindowAttributes(
                    self.hwnd_edge,
                    self.COLOR_KEY,
                    alpha,
                    win32con.LWA_COLORKEY | win32con.LWA_ALPHA,
                )

                # Animate tactical reticle & shockwave
                if self.shockwave_active:
                    s_elapsed = now - self.shockwave_start
                    duration = 0.25
                    if s_elapsed < duration:
                        progress = s_elapsed / duration
                        # Smooth cubic deceleration
                        ease_out = 1.0 - (1.0 - progress) ** 3
                        r = int(15 + ease_out * 27)
                        alpha_ratio = max(0.0, 1.0 - progress)
                        h_alpha = max(30, int(245 * alpha_ratio))
                        self._draw_tactical_reticle(
                            shockwave_radius=r,
                            shockwave_alpha_ratio=alpha_ratio,
                            flash_center=True,
                        )
                        win32gui.SetLayeredWindowAttributes(
                            self.hwnd_halo,
                            self.COLOR_KEY,
                            h_alpha,
                            win32con.LWA_COLORKEY | win32con.LWA_ALPHA,
                        )
                    else:
                        self.shockwave_active = False
                        self._draw_tactical_reticle()
                        win32gui.SetLayeredWindowAttributes(
                            self.hwnd_halo,
                            self.COLOR_KEY,
                            220,
                            win32con.LWA_COLORKEY | win32con.LWA_ALPHA,
                        )
                else:
                    self._draw_tactical_reticle()
                    win32gui.SetLayeredWindowAttributes(
                        self.hwnd_halo,
                        self.COLOR_KEY,
                        220,
                        win32con.LWA_COLORKEY | win32con.LWA_ALPHA,
                    )

                # Auto-idle timeout
                if now - self.last_action_time > self.auto_timeout_seconds:
                    self.state = "IDLE"

            elif self.state == "COMPLETING":
                elapsed = now - self.state_start
                if self.current_edge_mode != "COMPLETE":
                    self._draw_edge_bloom(self.COMPLETE_BLOOM_BANDS)
                    self.current_edge_mode = "COMPLETE"
                    win32gui.ShowWindow(self.hwnd_halo, win32con.SW_HIDE)

                if elapsed < 0.9:
                    # Flash vibrant emerald-mint aurora
                    win32gui.SetLayeredWindowAttributes(
                        self.hwnd_edge,
                        self.COLOR_KEY,
                        250,
                        win32con.LWA_COLORKEY | win32con.LWA_ALPHA,
                    )
                elif elapsed < 1.6:
                    # Smooth optical dissolution
                    fade_progress = (elapsed - 0.9) / 0.7
                    alpha = max(0, int(250 * (1.0 - fade_progress)))
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
                self.current_edge_mode = ""
                time.sleep(0.04)

            time.sleep(0.02)

        # Cleanup handles on exit
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

    def task_start(
        self,
        task_name: Optional[str] = None,
        monitor_index: int = 0,
        play_chime: bool = True,
    ) -> None:
        """
        Activates the cascading ambient screen edge bloom and tactical cursor reticle.
        Plays a subtle modern confirmation sound.
        """
        if not self.enabled:
            return
        self._ensure_worker()
        self.cmd_queue.put(("START", {"task_name": task_name, "monitor_index": monitor_index}))
        if play_chime:
            self.audio.play("start")
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
        Refreshes ambient active mode and updates cursor reticle coordinates / shockwaves.
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
        1. Screen perimeter erupts in an emerald-mint aurora bloom for ~1.5s then dissolves.
        2. Plays luxury glass marimba chord with acoustic resonance.
        3. Fades and dismisses cursor reticle.
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
