"""
Project Extra — Screen Capture Engine
High-speed screen buffer capture via hardware-accelerated and GDI pipelines,
supporting sub-30ms frame grabs, multi-monitor selection, ROI cropping,
and base64 encoding.
"""

from __future__ import annotations

import base64
import concurrent.futures
import io
import time
from dataclasses import dataclass
from typing import Optional, Tuple

import mss
from PIL import Image

from extra.core.geometry import (
    attach_input_desktop,
    clamp_coordinates,
    ensure_dpi_aware,
)


@dataclass
class CaptureResult:
    """Encapsulates captured screen image with performance metadata."""
    image: Image.Image
    duration_ms: float
    monitor_index: int
    width: int
    height: int
    crop_box: Optional[Tuple[int, int, int, int]] = None

    def to_base64(self, format: str = "JPEG", quality: int = 85) -> str:
        """Encodes captured PIL Image into base64 string."""
        return image_to_base64(self.image, format=format, quality=quality)


class ScreenCaptureEngine:
    """
    High-performance Windows screen capture engine.
    Uses an isolated background capture worker thread to avoid Win32 desktop
    security context contamination from COM apartments or UI message loops.
    """

    def __init__(self) -> None:
        ensure_dpi_aware()
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="ExtraCaptureWorker"
        )
        self._sct: Optional[mss.MSS] = None

    def _worker_grab(
        self,
        monitor_index: int,
        crop_box: Optional[Tuple[int, int, int, int]],
    ) -> Tuple[bytes, Tuple[int, int], str]:
        # Always attach the clean worker thread to the active input desktop
        attach_input_desktop()

        if self._sct is None:
            self._sct = mss.MSS()

        # mss.monitors[0] is all monitors combined, mss.monitors[1] is monitor 0
        mss_idx = monitor_index + 1
        if mss_idx < 1 or mss_idx >= len(self._sct.monitors):
            mss_idx = 1  # Fallback to primary monitor

        mon_info = self._sct.monitors[mss_idx]

        if crop_box:
            left, top, right, bottom = crop_box
            left, top = clamp_coordinates(left, top, monitor_index)
            right, bottom = clamp_coordinates(right, bottom, monitor_index)

            if right <= left or bottom <= top:
                region = mon_info
            else:
                region = {
                    "left": left,
                    "top": top,
                    "width": right - left,
                    "height": bottom - top,
                }
        else:
            region = mon_info

        raw_frame = self._sct.grab(region)
        return (bytes(raw_frame.bgra), raw_frame.size, "BGRX")

    def capture(
        self,
        monitor_index: int = 0,
        crop_box: Optional[Tuple[int, int, int, int]] = None,
    ) -> CaptureResult:
        """
        Captures a screen frame from the specified monitor.
        
        Args:
            monitor_index: 0-based index of monitor (0 = primary).
            crop_box: Optional (left, top, right, bottom) physical pixel bounding box.
            
        Returns:
            CaptureResult with PIL Image and latency stats.
        """
        ensure_dpi_aware()
        t_start = time.perf_counter()

        future = self._executor.submit(self._worker_grab, monitor_index, crop_box)
        bgra_bytes, size, raw_mode = future.result()

        img = Image.frombytes("RGB", size, bgra_bytes, "raw", raw_mode)
        duration_ms = (time.perf_counter() - t_start) * 1000.0

        return CaptureResult(
            image=img,
            duration_ms=round(duration_ms, 2),
            monitor_index=monitor_index,
            width=img.width,
            height=img.height,
            crop_box=crop_box,
        )

    def close(self) -> None:
        """Releases capture worker thread and resources."""
        def _cleanup():
            if self._sct is not None:
                try:
                    self._sct.close()
                except Exception:
                    pass
                self._sct = None

        try:
            self._executor.submit(_cleanup).result(timeout=1.0)
        except Exception:
            pass
        self._executor.shutdown(wait=False)

    def __enter__(self) -> "ScreenCaptureEngine":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


_default_engine: Optional[ScreenCaptureEngine] = None


def get_capture_engine() -> ScreenCaptureEngine:
    """Returns or initializes the shared ScreenCaptureEngine."""
    global _default_engine
    if _default_engine is None:
        _default_engine = ScreenCaptureEngine()
    return _default_engine


def capture_screen(
    monitor_index: int = 0,
    crop_box: Optional[Tuple[int, int, int, int]] = None,
) -> CaptureResult:
    """Convenience function to capture screen via default engine."""
    return get_capture_engine().capture(monitor_index=monitor_index, crop_box=crop_box)


def capture_roi(
    left: int, top: int, right: int, bottom: int, monitor_index: int = 0
) -> CaptureResult:
    """Convenience function to capture a specific region of interest."""
    return capture_screen(monitor_index=monitor_index, crop_box=(left, top, right, bottom))


def image_to_base64(image: Image.Image, format: str = "JPEG", quality: int = 85) -> str:
    """Converts a PIL Image to a base64 encoded string."""
    buffer = io.BytesIO()
    if format.upper() == "JPEG":
        if image.mode != "RGB":
            image = image.convert("RGB")
        image.save(buffer, format="JPEG", quality=quality, optimize=True)
    else:
        image.save(buffer, format=format)

    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return encoded
