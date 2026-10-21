"""
Project Extra — Semantic Accessibility Plane (PAL Facade)
Re-exports accessibility plane functions and classes from the active platform backend.
"""

from __future__ import annotations

from extra.core.platform import (
    AccessibilityPlane,
    SetOfMarkAnnotator,
    UIAutomationPlane,
    UIElement,
    get_accessibility_plane,
)

__all__ = [
    "AccessibilityPlane",
    "SetOfMarkAnnotator",
    "UIAutomationPlane",
    "UIElement",
    "get_accessibility_plane",
]
