"""
Project Extra — Task Indication & Feedback Subsystem (PAL Facade)
Re-exports indicator controllers and audio chimes from the active platform backend.
"""

from __future__ import annotations

from extra.core.platform import (
    AudioIndicator,
    IndicatorController,
    get_indicator_controller,
)

__all__ = [
    "AudioIndicator",
    "IndicatorController",
    "get_indicator_controller",
]
