"""
Project Extra — Screen Capture Engine (PAL Facade)
Re-exports screen capture functions and classes from the active platform backend.
"""

from __future__ import annotations

from extra.core.platform import (
    CaptureResult,
    ScreenCaptureEngine,
    capture_roi,
    capture_screen,
    get_capture_engine,
    image_to_base64,
)

__all__ = [
    "CaptureResult",
    "ScreenCaptureEngine",
    "capture_roi",
    "capture_screen",
    "get_capture_engine",
    "image_to_base64",
]
