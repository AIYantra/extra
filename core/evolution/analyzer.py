"""
Extra Evolution — Task Trajectory Analyzer
Evaluates execution traces for stalls, repetitive clicking, high vision overhead,
and novel workarounds to determine if a workflow should be crystallized into a skill.
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class TrajectoryAnalysis:
    """Quantitative and qualitative assessment of a task execution trace."""
    task_id: str
    total_steps: int = 0
    total_duration_ms: float = 0.0
    stall_count: int = 0
    screenshot_count: int = 0
    action_count: int = 0
    screenshot_ratio: float = 0.0
    friction_detected: bool = False
    friction_reasons: List[str] = field(default_factory=list)
    novelty_detected: bool = False
    candidate_for_evolution: bool = False
    is_golden_path: bool = True
    undo_count: int = 0
    suggested_playbook: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "total_steps": self.total_steps,
            "total_duration_ms": round(self.total_duration_ms, 2),
            "stall_count": self.stall_count,
            "screenshot_count": self.screenshot_count,
            "action_count": self.action_count,
            "screenshot_ratio": round(self.screenshot_ratio, 2),
            "friction_detected": self.friction_detected,
            "friction_reasons": self.friction_reasons,
            "novelty_detected": self.novelty_detected,
            "candidate_for_evolution": self.candidate_for_evolution,
            "is_golden_path": self.is_golden_path,
            "undo_count": self.undo_count,
            "suggested_playbook": self.suggested_playbook,
        }


def analyze_task_trajectory(
    task_id: str,
    events: List[Dict[str, Any]],
    success: bool = True,
    wall_clock_duration_ms: Optional[float] = None,
) -> TrajectoryAnalysis:
    """
    Analyzes task events to detect execution friction and opportunities for self-improvement.
    
    Args:
        task_id: Unique task identifier.
        events: Chronological sequence of step and stall events.
        success: Whether the overall task completed successfully.
        wall_clock_duration_ms: Total real elapsed wall-clock time between task_start and task_complete.
    """
    analysis = TrajectoryAnalysis(task_id=task_id, total_steps=len(events))

    if not events:
        if wall_clock_duration_ms is not None:
            analysis.total_duration_ms = wall_clock_duration_ms
        return analysis

    screenshot_count = 0
    action_count = 0
    stall_count = 0
    last_click_coord = None
    repeated_click_count = 0

    for ev in events:
        ev_type = ev.get("type", "")
        tool_name = ev.get("tool_name", "")
        duration = ev.get("duration_ms", 0) or 0
        analysis.total_duration_ms += duration

        # Count screenshots
        if "screenshot" in tool_name or "capture" in tool_name or ev_type == "screenshot":
            screenshot_count += 1
        elif tool_name:
            action_count += 1

        # Count stalls
        if ev_type == "stall" or "stall" in tool_name or ev.get("strike_count", 0) > 0:
            stall_count += 1
            trigger = ev.get("trigger_action") or ev.get("message") or "StallBreaker strike"
            analysis.friction_reasons.append(f"Stall detected: {trigger}")

        # Check for undo operations
        if "hotkey" in tool_name or ev_type == "hotkey":
            keys = [str(k).lower() for k in ev.get("keys", [])]
            if ("ctrl" in keys or "cmd" in keys) and "z" in keys:
                analysis.undo_count += 1
        elif "batch" in tool_name and "actions" in ev:
            for act in ev.get("actions", []):
                if isinstance(act, dict) and act.get("action") == "hotkey":
                    keys = [str(k).lower() for k in act.get("keys", [])]
                    if ("ctrl" in keys or "cmd" in keys) and "z" in keys:
                        analysis.undo_count += 1

        # Check for repetitive coordinate clicks (sign of visual coordinate hunting)
        if "click" in tool_name and "x" in ev and "y" in ev:
            x, y = ev["x"], ev["y"]
            if last_click_coord is not None:
                dist = math.hypot(x - last_click_coord[0], y - last_click_coord[1])
                if dist < 15.0:
                    repeated_click_count += 1
            last_click_coord = (x, y)

    analysis.screenshot_count = screenshot_count
    analysis.action_count = action_count
    analysis.stall_count = stall_count

    if action_count > 0:
        analysis.screenshot_ratio = screenshot_count / float(action_count)
    else:
        analysis.screenshot_ratio = float(screenshot_count)

    # Friction evaluation
    if stall_count > 0:
        analysis.friction_detected = True

    if analysis.undo_count > 0:
        analysis.friction_detected = True
        analysis.friction_reasons.append(f"Undo actions detected ({analysis.undo_count} undo operations).")

    if repeated_click_count >= 2:
        analysis.friction_detected = True
        analysis.friction_reasons.append(
            f"Repetitive clicking detected ({repeated_click_count} consecutive near-identical coordinates)."
        )

    if analysis.screenshot_ratio > 2.0 and action_count >= 3:
        analysis.friction_detected = True
        analysis.friction_reasons.append(
            f"Excessive visual overhead: {analysis.screenshot_ratio:.1f} screenshots per action (vision pixel-hunting)."
        )

    if analysis.total_steps > 20:
        analysis.friction_detected = True
        analysis.friction_reasons.append(
            f"High step count: task required {analysis.total_steps} steps."
        )

    # Check for severe unrecorded execution delays (background scripts / external stalls)
    sum_tool_duration_ms = analysis.total_duration_ms
    if wall_clock_duration_ms is not None and wall_clock_duration_ms > sum_tool_duration_ms:
        analysis.total_duration_ms = wall_clock_duration_ms
        unrecorded_delay_ms = wall_clock_duration_ms - sum_tool_duration_ms
        if unrecorded_delay_ms > 60_000 and (unrecorded_delay_ms > sum_tool_duration_ms * 3.0 or wall_clock_duration_ms > 120_000):
            analysis.friction_detected = True
            delay_sec = unrecorded_delay_ms / 1000.0
            analysis.friction_reasons.append(
                f"Severe unrecorded execution delay ({delay_sec:.1f}s gap between actions; background exploration, script execution, or external stall)."
            )

    # Golden Path Evaluation:
    # A true golden path has zero stalls, zero undos, zero repetitive click hunting, and compact step counts
    if (
        stall_count > 0
        or repeated_click_count > 0
        or analysis.undo_count > 0
        or analysis.screenshot_ratio > 1.5
        or analysis.total_steps > 25
        or analysis.friction_detected
    ):
        analysis.is_golden_path = False
    else:
        analysis.is_golden_path = True

    # Candidate for evolution:
    if success:
        if analysis.is_golden_path and not analysis.friction_detected:
            analysis.candidate_for_evolution = False  # standard clean run, no evolution needed
        else:
            # Succeeded but was NOT a clean golden path (heavy friction, undos, or high step count)
            analysis.is_golden_path = False
            analysis.candidate_for_evolution = True
            analysis.suggested_playbook = (
                "Task succeeded after overcoming execution friction (not a clean golden path). "
                "Synthesize ONLY discovered root-cause workarounds and anti-stall guardrails; "
                "do not record noisy intermediate recovery steps as a fast path."
            )
    else:
        analysis.candidate_for_evolution = True
        analysis.is_golden_path = False
        analysis.suggested_playbook = (
            "Task failed due to friction. Record app quirks and anti-stall guardrails to prevent recurrence."
        )

    return analysis
