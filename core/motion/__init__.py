"""
Project Extra — Biomechanical Motion & Human Trajectory Engine
Exports mathematical models for Bézier arcs, WindMouse physics, Fitts's Law profilers,
and continuous Catmull-Rom brush strokes.
"""

from __future__ import annotations

from extra.core.motion.curves import (
    apply_jitter,
    generate_bezier_path,
    generate_catmull_rom_spline,
)
from extra.core.motion.profiler import FittsProfiler
from extra.core.motion.stroke import generate_stroke_path
from extra.core.motion.windmouse import generate_windmouse_path

__all__ = [
    "apply_jitter",
    "generate_bezier_path",
    "generate_catmull_rom_spline",
    "generate_windmouse_path",
    "generate_stroke_path",
    "FittsProfiler",
]
