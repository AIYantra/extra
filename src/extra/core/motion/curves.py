"""
Project Extra — Biomechanical Curves & Spline Trajectory Engine
Pure-Python mathematical foundation for Bézier curves, Centripetal Catmull-Rom splines,
and physiological micro-tremor injection. Zero external dependencies.
"""

from __future__ import annotations

import math
import random
from typing import List, Tuple


Point = Tuple[int, int]
FloatPoint = Tuple[float, float]


def generate_bezier_path(
    start: Point,
    end: Point,
    steps: int = 25,
    deviation_factor: float = 0.25,
    control_points: int = 2,
) -> List[Point]:
    """
    Generates an organic cubic Bézier trajectory from start to end.
    Calculates control points with randomized orthogonal displacement
    proportional to the Euclidean travel distance, mimicking wrist/arm arcs.

    Args:
        start: Starting (x, y) coordinates.
        end: Target (x, y) coordinates.
        steps: Number of interpolated points along the curve.
        deviation_factor: Maximum perpendicular deviation ratio relative to chord distance.
        control_points: Number of internal control points (1 = quadratic, 2 = cubic).

    Returns:
        List of integer (x, y) pixel coordinates along the path.
    """
    x0, y0 = float(start[0]), float(start[1])
    x3, y3 = float(end[0]), float(end[1])

    dx = x3 - x0
    dy = y3 - y0
    distance = math.hypot(dx, dy)

    if distance < 3.0 or steps <= 1:
        return [start, end]

    # Unit vector along the chord and unit orthogonal vector
    ux = dx / distance
    uy = dy / distance
    perp_x = -uy
    perp_y = ux

    # Random deviation magnitude (positive or negative)
    max_dev = distance * deviation_factor
    dev1 = random.uniform(-max_dev, max_dev)
    dev2 = random.uniform(-max_dev * 0.7, max_dev * 0.7)

    # Control Point 1 (~1/3 of the way along the chord + orthogonal wander)
    cp1_dist = distance * random.uniform(0.25, 0.45)
    cp1_x = x0 + ux * cp1_dist + perp_x * dev1
    cp1_y = y0 + uy * cp1_dist + perp_y * dev1

    # Control Point 2 (~2/3 of the way along the chord + orthogonal wander)
    cp2_dist = distance * random.uniform(0.60, 0.85)
    cp2_x = x0 + ux * cp2_dist + perp_x * dev2
    cp2_y = y0 + uy * cp2_dist + perp_y * dev2

    path: List[Point] = []
    for i in range(steps + 1):
        t = i / float(steps)
        one_minus_t = 1.0 - t

        # Cubic Bézier formula:
        # B(t) = (1-t)^3 * P0 + 3(1-t)^2 * t * P1 + 3(1-t) * t^2 * P2 + t^3 * P3
        bx = (
            (one_minus_t ** 3) * x0
            + 3.0 * (one_minus_t ** 2) * t * cp1_x
            + 3.0 * one_minus_t * (t ** 2) * cp2_x
            + (t ** 3) * x3
        )
        by = (
            (one_minus_t ** 3) * y0
            + 3.0 * (one_minus_t ** 2) * t * cp1_y
            + 3.0 * one_minus_t * (t ** 2) * cp2_y
            + (t ** 3) * y3
        )
        path.append((int(round(bx)), int(round(by))))

    # Guarantee exact start and end coordinates
    if path:
        path[0] = start
        path[-1] = end
    return path


def generate_catmull_rom_spline(
    waypoints: List[Point],
    steps_per_segment: int = 15,
    alpha: float = 0.5,
) -> List[Point]:
    """
    Computes a centripetal Catmull-Rom spline passing smoothly through all waypoints.
    Essential for Canva brush painting, signatures, calligraphy, and timeline dragging.

    Centripetal Catmull-Rom (alpha = 0.5) eliminates self-intersections, cusps,
    and unnatural overshoot around sharp turns.

    Args:
        waypoints: List of (x, y) anchor points (must contain at least 2 points).
        steps_per_segment: Number of interpolated steps between each pair of waypoints.
        alpha: Spline knot parameterization (0.0 = uniform, 0.5 = centripetal, 1.0 = chordal).

    Returns:
        Smooth list of (x, y) coordinates passing through all waypoints.
    """
    if len(waypoints) < 2:
        return list(waypoints)
    if len(waypoints) == 2:
        # Direct interpolation
        return generate_bezier_path(waypoints[0], waypoints[1], steps=steps_per_segment)

    # Pad boundary endpoints so the curve interpolates through the first and last waypoints
    pts: List[FloatPoint] = (
        [(float(waypoints[0][0]), float(waypoints[0][1]))]
        + [(float(p[0]), float(p[1])) for p in waypoints]
        + [(float(waypoints[-1][0]), float(waypoints[-1][1]))]
    )

    def _knot(p1: FloatPoint, p2: FloatPoint, t_prev: float) -> float:
        dist = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        return t_prev + (dist ** alpha if dist > 0 else 1.0)

    result: List[Point] = []

    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]

        t0 = 0.0
        t1 = _knot(p0, p1, t0)
        t2 = _knot(p1, p2, t1)
        t3 = _knot(p2, p3, t2)

        for s in range(steps_per_segment):
            t = t1 + (t2 - t1) * (s / float(steps_per_segment))

            # Barycentric Catmull-Rom evaluation
            a1_x = ((t1 - t) * p0[0] + (t - t0) * p1[0]) / max(1e-6, t1 - t0)
            a1_y = ((t1 - t) * p0[1] + (t - t0) * p1[1]) / max(1e-6, t1 - t0)
            a2_x = ((t2 - t) * p1[0] + (t - t1) * p2[0]) / max(1e-6, t2 - t1)
            a2_y = ((t2 - t) * p1[1] + (t - t1) * p2[1]) / max(1e-6, t2 - t1)
            a3_x = ((t3 - t) * p2[0] + (t - t2) * p3[0]) / max(1e-6, t3 - t2)
            a3_y = ((t3 - t) * p2[1] + (t - t2) * p3[1]) / max(1e-6, t3 - t2)

            b1_x = ((t2 - t) * a1_x + (t - t0) * a2_x) / max(1e-6, t2 - t0)
            b1_y = ((t2 - t) * a1_y + (t - t0) * a2_y) / max(1e-6, t2 - t0)
            b2_x = ((t3 - t) * a2_x + (t - t1) * a3_x) / max(1e-6, t3 - t1)
            b2_y = ((t3 - t) * a2_y + (t - t1) * a3_y) / max(1e-6, t3 - t1)

            cx = ((t2 - t) * b1_x + (t - t1) * b2_x) / max(1e-6, t2 - t1)
            cy = ((t2 - t) * b1_y + (t - t1) * b2_y) / max(1e-6, t2 - t1)

            result.append((int(round(cx)), int(round(cy))))

    result.append(waypoints[-1])
    return result


def apply_jitter(
    points: List[Point],
    amplitude: float = 1.2,
    frequency: float = 0.4,
) -> List[Point]:
    """
    Overlays high-frequency Gaussian micro-tremor noise (physiological 8-12 Hz hand tremors)
    onto a coordinate sequence while anchoring the start and target endpoints.

    Args:
        points: Path coordinates.
        amplitude: Standard deviation of pixel deviation.
        frequency: Probability of applying tremor on each step.

    Returns:
        Coordinates with natural micro-tremor variations.
    """
    if len(points) <= 2:
        return points

    jittered: List[Point] = [points[0]]
    n = len(points)

    for i in range(1, n - 1):
        x, y = points[i]
        # Taper off jitter near start and target destination
        progress = i / float(n)
        damp = math.sin(progress * math.pi)  # 0 at start/end, 1 in middle

        if random.random() < frequency:
            jx = random.gauss(0, amplitude * damp)
            jy = random.gauss(0, amplitude * damp)
            jittered.append((int(round(x + jx)), int(round(y + jy))))
        else:
            jittered.append((x, y))

    jittered.append(points[-1])
    return jittered
