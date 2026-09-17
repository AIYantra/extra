"""
Extra Evolution Subsystem — Self-Improving Learning Loop & Curator
Analyzes execution trajectories, detects stalls and friction, crystallizes
novel fast-paths into permanent skills, and curates the skill library.
"""

from extra.core.evolution.analyzer import analyze_task_trajectory, TrajectoryAnalysis
from extra.core.evolution.crystallizer import crystallize_skill_evolution
from extra.core.evolution.curator import curate_skill_library

__all__ = [
    "analyze_task_trajectory",
    "TrajectoryAnalysis",
    "crystallize_skill_evolution",
    "curate_skill_library",
]
