"""
Project Extra — Linux Screen Perception Engine
High-speed screen buffer capture supporting Wayland (KDE KWin ScreenShot2, spectacle, grim)
and X11 (MIT-SHM via mss, scrot), multi-monitor selection, ROI cropping,
active window telemetry, and base64 encoding.
"""

from __future__ import annotations

import io
import logging
import os
import shutil
import subprocess
import time
from typing import Any, Dict, Optional, Tuple

try:
    from PIL import Image
except ImportError:
    Image = None

from extra.core.platform.base import (
    AbstractCaptureEngine,
    CaptureResult,
    image_to_base64,
)
from extra.core.platform.linux.geometry import (
    clamp_coordinates,
    get_monitors_info,
)
from extra.core.platform.linux.permissions import is_wayland

logger = logging.getLogger("extra.capture.linux")

_engine_instance: Optional[ScreenCaptureEngine] = None


class ScreenCaptureEngine(AbstractCaptureEngine):
    """
    High-performance Linux screen perception engine.
    Dynamically routes between Wayland compositor tools (spectacle, grim, KWin)
    and X11 MIT-SHM shared memory capture via mss.
    """

    def __init__(self) -> None:
        self._is_wayland = is_wayland()
        self._sct = None

    def _get_active_window_telemetry(self) -> Tuple[str, int]:
        """
        Retrieves active foreground window title and window ID for telemetry.
        Safely attempts focus manager lookup without circular dependencies.
        """
        try:
            from extra.core.platform.linux.focus import get_foreground_window
            win = get_foreground_window()
            if win:
                return win.title, win.hwnd
        except Exception:
            pass
        return "Desktop", 0

    def _capture_wayland(self, crop_box: Optional[Tuple[int, int, int, int]] = None) -> Optional[Image.Image]:
        """Captures display on Wayland using compositor utilities (spectacle, grim)."""
        if Image is None:
            raise RuntimeError("Pillow is required for screen capture decoding on Linux.")

        # 1. Try spectacle on KDE Wayland
        if shutil.which("spectacle"):
            cmd = ["spectacle", "-b", "-n", "-o", "/dev/stdout"]
            try:
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=4.0)
                if proc.returncode == 0 and len(proc.stdout) > 0:
                    img = Image.open(io.BytesIO(proc.stdout))
                    return img.convert("RGB")
            except Exception as e:
                logger.debug(f"Spectacle capture failed: {e}")

        # 2. Try grim on wlroots / Sway / Hyprland Wayland
        if shutil.which("grim"):
            cmd = ["grim", "-"]
            if crop_box:
                x1, y1, x2, y2 = crop_box
                cmd = ["grim", "-g", f"{x1},{y1} {x2-x1}x{y2-y1}", "-"]
            try:
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2.0)
                if proc.returncode == 0 and len(proc.stdout) > 0:
                    img = Image.open(io.BytesIO(proc.stdout))
                    return img.convert("RGB")
            except Exception as e:
                logger.debug(f"Grim capture failed: {e}")

        return None

    def _capture_x11(
        self, monitor_index: int, crop_box: Optional[Tuple[int, int, int, int]] = None
    ) -> Optional[Image.Image]:
        """Captures display on X11 via mss with MIT-SHM shared memory."""
        if Image is None:
            raise RuntimeError("Pillow is required for screen capture decoding on Linux.")

        try:
            import mss
            if self._sct is None:
                self._sct = mss.mss()

            mss_idx = monitor_index + 1
            if mss_idx < 1 or mss_idx >= len(self._sct.monitors):
                mss_idx = 1

            mon = self._sct.monitors[mss_idx]
            if crop_box:
                x1, y1, x2, y2 = crop_box
                w = max(1, x2 - x1)
                h = max(1, y2 - y1)
                region = {"left": x1, "top": y1, "width": w, "height": h}
            else:
                region = mon

            sct_img = self._sct.grab(region)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            return img
        except Exception as e:
            logger.debug(f"mss X11 capture failed: {e}")

        # Fallback to scrot CLI
        if shutil.which("scrot"):
            try:
                proc = subprocess.run(["scrot", "-o", "-"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2.0)
                if proc.returncode == 0 and len(proc.stdout) > 0:
                    img = Image.open(io.BytesIO(proc.stdout))
                    return img.convert("RGB")
            except Exception as e:
                logger.debug(f"scrot capture failed: {e}")

        return None

    def capture(
        self,
        monitor_index: int = 0,
        crop_box: Optional[Tuple[int, int, int, int]] = None,
    ) -> CaptureResult:
        """
        Captures a screen frame from the target display.
        Returns a CaptureResult dataclass containing the PIL Image and performance metadata.
        """
        t0 = time.perf_counter()
        img: Optional[Image.Image] = None

        if self._is_wayland:
            img = self._capture_wayland(crop_box=crop_box)
            # If wayland tool failed, try X11 fallback (e.g. XWayland root)
            if img is None:
                img = self._capture_x11(monitor_index=monitor_index, crop_box=crop_box)
        else:
            img = self._capture_x11(monitor_index=monitor_index, crop_box=crop_box)
            if img is None:
                img = self._capture_wayland(crop_box=crop_box)

        # Fallback empty image if no capture provider was available
        if img is None:
            logger.warning("All Linux screen capture pipelines failed; generating fallback image.")
            monitors = get_monitors_info()
            mon = monitors[monitor_index] if 0 <= monitor_index < len(monitors) else monitors[0]
            if Image is not None:
                img = Image.new("RGB", (mon.width, mon.height), color=(30, 30, 30))
            else:
                raise RuntimeError("No image libraries available on host to decode screen capture.")

        # Handle post-crop if crop_box specified and capture was full-frame
        if crop_box and (img.size != (crop_box[2] - crop_box[0], crop_box[3] - crop_box[1])):
            x1, y1 = clamp_coordinates(crop_box[0], crop_box[1], monitor_index)
            x2, y2 = clamp_coordinates(crop_box[2], crop_box[3], monitor_index)
            if x2 > x1 and y2 > y1:
                img = img.crop((x1, y1, x2, y2))

        duration_ms = (time.perf_counter() - t0) * 1000.0

        res = CaptureResult(
            image=img,
            duration_ms=duration_ms,
            monitor_index=monitor_index,
            width=img.width,
            height=img.height,
            crop_box=crop_box,
        )

        # Append active window perception telemetry (v0.3.0 standard)
        title, hwnd = self._get_active_window_telemetry()
        setattr(res, "active_window_title", title)
        setattr(res, "active_window_hwnd", hwnd)

        return res

    def close(self) -> None:
        if self._sct is not None:
            try:
                self._sct.close()
            except Exception:
                pass
            self._sct = None


def get_capture_engine() -> ScreenCaptureEngine:
    """Returns the singleton ScreenCaptureEngine for Linux."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = ScreenCaptureEngine()
    return _engine_instance


def capture_screen(
    monitor_index: int = 0,
    crop_box: Optional[Tuple[int, int, int, int]] = None,
) -> CaptureResult:
    """Captures the screen and returns a CaptureResult."""
    return get_capture_engine().capture(monitor_index=monitor_index, crop_box=crop_box)


def capture_roi(
    left: int,
    top: int,
    right: int,
    bottom: int,
    monitor_index: int = 0,
) -> CaptureResult:
    """Captures a specific Region of Interest (ROI) by bounding box."""
    return capture_screen(
        monitor_index=monitor_index, crop_box=(left, top, right, bottom)
    )
