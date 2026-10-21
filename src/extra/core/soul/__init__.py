"""
Project Extra — Project SOUL (System One Ultra-fast Layer)
Sub-second on-device unified logic for desktop automation reflexes.
"""

from __future__ import annotations

from extra.core.soul.critic import CriticVerdict, SoulCritic, evaluate_screen_milestone
from extra.core.soul.decider import SoulDecider, get_soul_decider
from extra.core.soul.eyes import SoulEyes, get_soul_eyes, visual_ground
from extra.core.soul.gateman import SoulGateman, wait_until_settled
from extra.core.soul.compressor import SoulCompressor, compress_milestone_state
from extra.core.soul.runtime import SoulRuntimeManager, get_soul_runtime
from extra.core.soul.vision_parser import (
    EdgeVisionParser,
    detect_canvas_viewport,
    parse_opaque_canvas,
)
from extra.core.soul.schemas import (
    DecisionType,
    GroundingResult,
    SoulBoundingBox,
    SoulDecision,
    WorkSurfaceViewport,
)

from extra.core.soul.state_critic import (
    GroundTruthStateCritic,
    StateAuditClaim,
    StateAuditResult,
    audit_ground_truth_state,
)

__all__ = [
    "DecisionType",
    "SoulDecision",
    "SoulBoundingBox",
    "GroundingResult",
    "WorkSurfaceViewport",
    "SoulRuntimeManager",
    "get_soul_runtime",
    "SoulDecider",
    "get_soul_decider",
    "SoulEyes",
    "get_soul_eyes",
    "visual_ground",
    "EdgeVisionParser",
    "parse_opaque_canvas",
    "detect_canvas_viewport",
    "SoulGateman",
    "wait_until_settled",
    "SoulCritic",
    "CriticVerdict",
    "evaluate_screen_milestone",
    "SoulCompressor",
    "compress_milestone_state",
    "GroundTruthStateCritic",
    "StateAuditClaim",
    "StateAuditResult",
    "audit_ground_truth_state",
]


