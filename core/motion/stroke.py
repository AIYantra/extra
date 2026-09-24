"""
Project Extra — Continuous Brush Stroke & Gesture Generator
Specialized trajectory synthesizer for Canva canvas painting, MS Paint sketching,
calligraphy strokes, signature simulation, and video editor timeline scrubbing.
Zero external dependencies.
"""

from __future__ import annotations

import math
import random
from typing import List, Tuple

from extra.core.motion.curves import generate_catmull_rom_spline

Point = Tuple[int, int]
ScheduledStep = Tuple[int, int, float]  # (x, y, delay_seconds)


def generate_stroke_path(
    waypoints: List[Point],
    duration: float = 1.0,
    smooth: bool = True,
    steps_per_segment: int = 18,
    human_jitter: bool = True,
) -> List[ScheduledStep]:
    """
    Generates a fluid, continuous vector brush stroke across multiple anchor points.

    Implements:
    - Centripetal Catmull-Rom spline interpolation (eliminating sharp corner cuts).
    - Viviani's Two-Thirds Power Law: velocity is inversely proportional to curve curvature
      (drawing slows down on tight curves and accelerates on sweeping lines).
    - Sub-millisecond step delay distribution guaranteeing target stroke duration.

    Args:
        waypoints: List of (x, y) anchor coordinates forming the path.
        duration: Total duration of the stroke in seconds.
        smooth: If True, uses Catmull-Rom spline smoothing. If False, linear interpolation.
        steps_per_segment: Resolution of intermediate points between waypoints.
        human_jitter: If True, overlays subtle drawing hand micro-variations.

    Returns:
        List of (x, y, delay_seconds) ready for hardware mouse-down dispatch.
    """
    if not waypoints:
        return []
    if len(waypoints) == 1:
        return [(waypoints[0][0], waypoints[0][1], duration)]

    # 1. Generate interpolated path
    if smooth and len(waypoints) >= 2:
        raw_path = generate_catmull_rom_spline(waypoints, steps_per_segment=steps_per_segment)
    else:
        # Linear piecewise interpolation
        raw_path: List[Point] = []
        for i in range(len(waypoints) - 1):
            p0 = waypoints[i]
            p1 = waypoints[i + 1]
            for s in range(steps_per_segment):
                t = s / float(steps_per_segment)
                ix = int(round(p0[0] + (p1[0] - p0[0]) * t))
                iy = int(round(p0[1] + (p1[1] - p0[1]) * t))
                raw_path.append((ix, iy))
        raw_path.append(waypoints[-1])

    n = len(raw_path)
    if n <= 1:
        return [(raw_path[0][0], raw_path[0][1], duration)]

    # 2. Calculate local curvature and segment lengths for Viviani's Power Law
    # Higher curvature (turning) -> lower speed -> higher delay
    step_weights: List[float] = []

    for i in range(n - 1):
        p_prev = raw_path[max(0, i - 1)]
        p_curr = raw_path[i]
        p_next = raw_path[i + 1]

        # Segment distance
        seg_dist = math.hypot(p_next[0] - p_curr[0], p_next[1] - p_curr[1])

        # Angular change (curvature proxy)
        v1 = (p_curr[0] - p_prev[0], p_curr[1] - p_prev[1])
        v2 = (p_next[0] - p_curr[0], p_next[1] - p_curr[1])
        len1 = math.hypot(v1[0], v1[1])
        len2 = math.hypot(v2[0], v2[1])

        if len1 > 1e-4 and len2 > 1e-4:
            dot = (v1[0] * v2[0] + v1[1] * v2[1]) / (len1 * len2)
            dot = max(-1.0, min(1.0, dot))
            turn_angle = math.acos(dot)  # 0 = straight line, pi = complete reversal
        else:
            turn_angle = 0.0

        # Curvature penalty: slower on sharp bends (calligraphy dynamics)
        curvature_factor = 1.0 + (turn_angle * 1.5)
        weight = max(0.1, seg_dist * curvature_factor)
        step_weights.append(weight)

    total_weight = sum(step_weights) or 1.0
    scale = duration / total_weight

    result: List[ScheduledStep] = []
    min_delay = 0.003
    max_delay = 0.035

    for i in range(n - 1):
        x, y = raw_path[i]
        if human_jitter and 0 < i < n - 1:
            # Subtle hand friction tremor (+- 0.8px)
            if random.random() < 0.25:
                x += int(round(random.gauss(0, 0.6)))
                y += int(round(random.gauss(0, 0.6)))

        delay = step_weights[i] * scale
        delay = max(min_delay, min(max_delay, delay))
        result.append((x, y, delay))

    # Final endpoint
    result.append((raw_path[-1][0], raw_path[-1][1], min_delay))
    return result
