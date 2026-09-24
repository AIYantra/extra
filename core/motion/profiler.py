"""
Project Extra — Fitts's Law Velocity Profiler & Motor Control Engine
Models asymmetric Minimum Jerk velocity curves, target overshooting,
and non-linear anti-bot delay distributions. Zero external dependencies.
"""

from __future__ import annotations

import math
import random
from typing import List, Optional, Tuple

Point = Tuple[int, int]
ScheduledStep = Tuple[int, int, float]  # (x, y, delay_seconds)


class FittsProfiler:
    """
    Computes biomechanical timing and velocity profiles for cursor movements.
    Implements:
    - Fitts's Law movement time scaling: T = a + b * log2(Distance / TargetSize + 1).
    - Flash & Hogan Minimum Jerk trajectory velocity curves.
    - Probabilistic target overshoot and corrective saccades.
    - Stochastic jitter to evade fixed-polling anti-bot heuristics.
    """

    @staticmethod
    def calculate_duration(
        distance: float,
        speed: str = "normal",
        target_size: float = 24.0,
    ) -> float:
        """
        Calculates realistic movement duration in seconds based on Fitts's Law.

        Args:
            distance: Euclidean distance in physical pixels.
            speed: Speed profile preset ("fast", "normal", "slow").
            target_size: Effective width of the target UI element.

        Returns:
            Duration in seconds (e.g. 0.18s to 0.75s).
        """
        if distance < 5.0:
            return 0.04

        # Index of Difficulty (Shannon formulation)
        id_bits = math.log2((distance / max(1.0, target_size)) + 1.0)

        # Baseline parameters (a = reaction intercept, b = motor index)
        if speed == "fast":
            a, b = 0.08, 0.035
        elif speed == "slow":
            a, b = 0.28, 0.090
        else:  # "normal"
            a, b = 0.16, 0.055

        duration = a + b * id_bits
        # Add slight natural human variability (+- 10%)
        duration *= random.uniform(0.92, 1.08)
        return max(0.06, min(1.2, duration))

    @staticmethod
    def schedule_path(
        points: List[Point],
        total_duration: float,
        min_step_delay: float = 0.004,
        max_step_delay: float = 0.016,
    ) -> List[ScheduledStep]:
        """
        Schedules a sequence of coordinate points with Minimum Jerk velocity delays.

        In human motor control, acceleration is rapid (~30% of time) and deceleration
        is prolonged (~70% of time) as the hand settles onto the target.

        Args:
            points: List of (x, y) coordinates along the path.
            total_duration: Desired total trajectory duration in seconds.
            min_step_delay: Minimum delay per step (preventing CPU pegging).
            max_step_delay: Maximum delay per step.

        Returns:
            List of (x, y, delay_seconds) ready for platform hardware dispatch.
        """
        n = len(points)
        if n == 0:
            return []
        if n == 1:
            return [(points[0][0], points[0][1], 0.01)]

        steps: List[ScheduledStep] = []
        raw_delays: List[float] = []

        # Generate asymmetric Minimum Jerk velocity weighting:
        # v(tau) = 30 * tau^2 * (1 - tau)^2, skewed toward deceleration near end
        for i in range(n - 1):
            tau = i / float(max(1, n - 1))
            # Skew peak velocity to tau = 0.38 (faster acceleration, slower approach)
            skewed_tau = math.pow(tau, 0.85)
            # Velocity proxy (normalized)
            v = 30.0 * (skewed_tau ** 2) * ((1.0 - min(1.0, skewed_tau)) ** 2)
            v = max(0.08, v)

            # Inversely proportional: high velocity = short delay; slow velocity = long delay
            delay_weight = 1.0 / v
            # Add stochastic non-linear perturbation (+- 15%) to break bot detection
            delay_weight *= random.uniform(0.85, 1.15)
            raw_delays.append(delay_weight)

        total_weight = sum(raw_delays) or 1.0
        scale = total_duration / total_weight

        for i in range(n - 1):
            delay = raw_delays[i] * scale
            delay = max(min_step_delay, min(max_step_delay, delay))
            steps.append((points[i][0], points[i][1], delay))

        # Final target step: settling delay
        settle_delay = random.uniform(0.015, 0.035)
        steps.append((points[-1][0], points[-1][1], settle_delay))
        return steps

    @staticmethod
    def generate_overshoot(
        start: Point,
        end: Point,
        distance: float,
        probability: float = 0.20,
    ) -> Optional[Point]:
        """
        Calculates a natural human overshoot point beyond the target.
        Humans moving at moderate-to-high velocity frequently overshoot the destination
        by 2-7% of travel distance before executing a rapid corrective saccade.

        Args:
            start: Start coordinate.
            end: Target coordinate.
            distance: Distance between start and end.
            probability: Probability of overshooting.

        Returns:
            Overshoot point (x, y) or None if no overshoot occurs.
        """
        if distance < 80.0 or random.random() > probability:
            return None

        # Overshoot magnitude: 3 to 12 pixels depending on distance
        overshoot_mag = min(14.0, max(3.0, distance * random.uniform(0.02, 0.06)))

        dx = end[0] - start[0]
        dy = end[1] - start[1]
        dist = math.hypot(dx, dy)
        if dist < 1.0:
            return None

        ux = dx / dist
        uy = dy / dist

        # Add slight lateral drift to the overshoot vector
        lateral_drift = random.uniform(-overshoot_mag * 0.4, overshoot_mag * 0.4)
        perp_x = -uy
        perp_y = ux

        ox = int(round(end[0] + ux * overshoot_mag + perp_x * lateral_drift))
        oy = int(round(end[1] + uy * overshoot_mag + perp_y * lateral_drift))
        return (ox, oy)
