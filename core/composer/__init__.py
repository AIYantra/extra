"""
Project Extra — Core Composer & Hierarchical Task Engine
Universal System 2 Task-State DAG, Hierarchical Information Folding (HIPIF),
and Milestone Verification Subsystem.
"""

from __future__ import annotations

from extra.core.composer.blueprint import (
    Milestone,
    MilestoneStatus,
    TaskBlueprint,
    TaskDAG,
)
from extra.core.composer.folding import (
    HIPIFFolder,
    StateCheckpoint,
    create_semantic_state_token,
    fold_completed_milestone,
)
from extra.core.composer.verifier import (
    MilestoneVerifier,
    VerificationResult,
    verify_milestone_acceptance,
)

__all__ = [
    "Milestone",
    "MilestoneStatus",
    "TaskBlueprint",
    "TaskDAG",
    "HIPIFFolder",
    "StateCheckpoint",
    "create_semantic_state_token",
    "fold_completed_milestone",
    "MilestoneVerifier",
    "VerificationResult",
    "verify_milestone_acceptance",
]
