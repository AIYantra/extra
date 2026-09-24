"""
Extra Evolution Subsystem — Self-Improving Learning Loop & Curator
Analyzes execution trajectories, detects stalls and friction, crystallizes
novel fast-paths into permanent skills, and curates the skill library.
"""

from extra.core.evolution.analyzer import analyze_task_trajectory, TrajectoryAnalysis
from extra.core.evolution.crystallizer import crystallize_skill_evolution, crystallize_soul_fastpath
from extra.core.evolution.curator import (
    clean_skill_content,
    curate_skill_library,
    ensure_startup_migration,
    get_default_skill_directories,
    sanitize_skill_library,
)
from extra.core.evolution.api_synthesizer import ApiSynthesizer

__all__ = [
    "analyze_task_trajectory",
    "TrajectoryAnalysis",
    "crystallize_skill_evolution",
    "crystallize_soul_fastpath",
    "curate_skill_library",
    "sanitize_skill_library",
    "clean_skill_content",
    "ensure_startup_migration",
    "get_default_skill_directories",
    "ApiSynthesizer",
]

