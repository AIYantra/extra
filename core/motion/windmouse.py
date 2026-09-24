"""
Project Extra — WindMouse Physics Trajectory Generator
Based on Benjamin Land's physics simulation modeling mass, gravitational attraction,
and Brownian wind turbulence for organic human cursor simulation. Zero external dependencies.
"""

from __future__ import annotations

import math
import random
from typing import List, Tuple

Point = Tuple[int, int]
Step = Tuple[int, int, float]  # (x, y, sleep_seconds)


def generate_windmouse_path(
    start: Point,
    end: Point,
    gravity: float = 9.0,
    wind: float = 3.0,
    min_wait: float = 0.003,
    max_wait: float = 0.009,
    max_step: float = 12.0,
    target_area: float = 12.0,
) -> List[Step]:
    """
    Generates a physics-based human cursor path using the WindMouse algorithm.

    Simulates the cursor as a physical mass influenced by:
    - Gravitational attraction pulling toward the target coordinate.
    - Fluctuating Brownian wind currents simulating biomechanical hand wander and tremors.
    - Inertial damping preventing abrupt or robotic velocity discontinuities.

    Args:
        start: Starting (x, y) coordinates.
        end: Destination (x, y) coordinates.
        gravity: Force magnitude pulling the cursor toward the destination.
        wind: Magnitude of random wind force generating natural wander.
        min_wait: Minimum sleep delay per movement step in seconds.
        max_wait: Maximum sleep delay per movement step in seconds.
        max_step: Maximum pixel displacement per step during ballistic travel.
        target_area: Radius around destination where gravity and wind taper for fine landing.

    Returns:
        List of (x, y, delay_seconds) steps along the trajectory.
    """
    cur_x, cur_y = float(start[0]), float(start[1])
    dest_x, dest_y = float(end[0]), float(end[1])

    dist = math.hypot(dest_x - cur_x, dest_y - cur_y)
    if dist < 2.0:
        return [(end[0], end[1], min_wait)]

    vx = 0.0
    vy = 0.0
    wind_x = 0.0
    wind_y = 0.0

    sqrt3 = math.sqrt(3.0)
    sqrt5 = math.sqrt(5.0)

    steps: List[Step] = [(start[0], start[1], min_wait)]
    max_iterations = 800
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        dist = math.hypot(dest_x - cur_x, dest_y - cur_y)
        if dist < 2.5:
            break

        # Adjust wind and gravity when approaching target landing radius
        if dist >= target_area:
            w_mag = min(wind, dist)
            wind_x = wind_x / sqrt3 + (random.random() * (w_mag * 2.0 + 1.0) - w_mag) / sqrt5
            wind_y = wind_y / sqrt3 + (random.random() * (w_mag * 2.0 + 1.0) - w_mag) / sqrt5
        else:
            wind_x /= sqrt3
            wind_y /= sqrt3
            if max_step < 3.0:
                max_step = random.random() * 3.0 + 3.0
            else:
                max_step /= sqrt5

        # Gravitational attraction towards target
        grav_x = (dest_x - cur_x) * gravity / max(1.0, dist)
        grav_y = (dest_y - cur_y) * gravity / max(1.0, dist)

        # Update velocities with inertia damping
        vx += wind_x + grav_x
        vy += wind_y + grav_y

        v_mag = math.hypot(vx, vy)
        if v_mag > max_step:
            v_clip = (max_step / 2.0) + (random.random() * max_step / 2.0)
            vx = (vx / v_mag) * v_clip
            vy = (vy / v_mag) * v_clip

        cur_x += vx
        cur_y += vy

        # Asymmetric wait delay based on current speed (simulating fine motor control)
        speed_ratio = min(1.0, v_mag / max(1.0, max_step))
        # Moving faster = shorter delay between samples; decelerating = slightly longer pauses
        delay = max_wait - (speed_ratio * (max_wait - min_wait)) + random.uniform(-0.0005, 0.0005)
        delay = max(min_wait, min(max_wait * 1.5, delay))

        steps.append((int(round(cur_x)), int(round(cur_y)), delay))

    # Guarantee clean arrival on target
    steps.append((end[0], end[1], max_wait))
    return steps
