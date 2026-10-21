"""
Project Extra — Hierarchical Information Folding (HIPIF) Subsystem
Compresses long-horizon execution trajectories, folds completed subgoals into
dense semantic state tokens, and maintains durable checkpoints to eliminate context drift.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from extra.core.composer.blueprint import Milestone, MilestoneStatus, TaskBlueprint

logger = logging.getLogger("Extra-Composer-Folding")

_EXTRA_HOME = Path(os.environ.get("USERPROFILE") or os.environ.get("HOME") or ".") / ".extra"
_CHECKPOINTS_DIR = _EXTRA_HOME / "checkpoints"


@dataclass
class StateCheckpoint:
    """
    A persistent, durable checkpoint representing an immutable task milestone boundary.
    """
    task_id: str
    checkpoint_id: str
    milestone_id: str
    completed_milestones: List[str]
    pending_milestones: List[str]
    accumulated_artifacts: List[str]
    state_summary: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StateCheckpoint:
        return cls(**data)


def create_semantic_state_token(
    milestone: Milestone,
    artifacts: Optional[List[str]] = None,
    custom_status: str = "OK",
) -> str:
    """
    Creates a dense, 10-15 word semantic token representing a completed milestone.
    Used to inform host LLMs without flooding their context with verbose logs.
    """
    art_str = f" | artifacts: {len(artifacts or milestone.expected_artifacts)}" if (artifacts or milestone.expected_artifacts) else ""
    return f"[MILESTONE_COMPLETE: {milestone.id} | name: '{milestone.name}'{art_str} | status: {custom_status}]"


class HIPIFFolder:
    """
    Hierarchical Information Folding Engine (HIPIF).
    Prunes transient perception and execution logs from completed subgoals,
    preserving global task context in a clean, compact representation.
    """

    def __init__(self, checkpoints_dir: Optional[Path] = None) -> None:
        self.checkpoints_dir = checkpoints_dir or _CHECKPOINTS_DIR
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)

    def fold_milestone(
        self,
        blueprint: TaskBlueprint,
        milestone_id: str,
        summary: Optional[str] = None,
        artifacts: Optional[List[str]] = None,
    ) -> StateCheckpoint:
        """
        Folds a newly completed milestone into a durable checkpoint and updates state.
        """
        if milestone_id not in blueprint.milestones:
            raise KeyError(f"Milestone '{milestone_id}' not found in blueprint")

        m = blueprint.milestones[milestone_id]
        if m.status != MilestoneStatus.COMPLETED:
            blueprint.complete_milestone(milestone_id)

        completed = [
            m_id for m_id, item in blueprint.milestones.items()
            if item.status in (MilestoneStatus.COMPLETED, MilestoneStatus.SKIPPED)
        ]
        pending = [
            m_id for m_id, item in blueprint.milestones.items()
            if item.status == MilestoneStatus.PENDING
        ]

        all_artifacts = set()
        for c_id in completed:
            all_artifacts.update(blueprint.milestones[c_id].expected_artifacts)
        if artifacts:
            all_artifacts.update(artifacts)

        ckpt_id = f"ckpt_{milestone_id}_{int(time.time())}"
        state_summary = summary or f"Completed milestone '{m.name}' successfully."

        checkpoint = StateCheckpoint(
            task_id=blueprint.task_id,
            checkpoint_id=ckpt_id,
            milestone_id=milestone_id,
            completed_milestones=completed,
            pending_milestones=pending,
            accumulated_artifacts=sorted(list(all_artifacts)),
            state_summary=state_summary,
            metadata={"title": blueprint.title, "task_type": blueprint.task_type},
        )

        # Save checkpoint to disk
        ckpt_file = self.checkpoints_dir / f"{blueprint.task_id}.json"
        ckpt_file.write_text(json.dumps(checkpoint.to_dict(), indent=2), encoding="utf-8")
        logger.info("[HIPIF] Saved checkpoint '%s' for task '%s'", ckpt_id, blueprint.task_id)
        return checkpoint

    def generate_folded_prompt(self, blueprint: TaskBlueprint) -> str:
        """
        Generates a compact, high-density status block to inject into the LLM context.
        Replaces hundreds of previous turn logs with a structured markdown summary.
        """
        total = len(blueprint.milestones)
        completed_count = sum(
            1 for m in blueprint.milestones.values()
            if m.status in (MilestoneStatus.COMPLETED, MilestoneStatus.SKIPPED)
        )

        lines = [
            f"### [HIPIF Task Context: {blueprint.title}] (Progress: {completed_count}/{total})",
            f"Task ID: `{blueprint.task_id}` | Type: `{blueprint.task_type}`",
            "",
            "**Milestone Pipeline:**",
        ]

        for m_id, m in blueprint.milestones.items():
            if m.status == MilestoneStatus.COMPLETED:
                badge = "[DONE]"
            elif m.status == MilestoneStatus.RUNNING:
                badge = "[IN PROGRESS]"
            elif m.status == MilestoneStatus.FAILED:
                badge = "[FAILED]"
            elif m.status == MilestoneStatus.SKIPPED:
                badge = "[SKIPPED]"
            else:
                badge = "[TODO]"

            lines.append(f"- {badge} **{m.id}** ({m.name}): {m.description}")

        runnable = blueprint.get_next_runnable()
        if runnable:
            lines.append("")
            lines.append(f"**Next Runnable Milestone:** `{runnable[0].id}` — *{runnable[0].name}*")
        elif blueprint.is_complete:
            lines.append("")
            lines.append("**Status:** ALL MILESTONES COMPLETE.")

        return "\n".join(lines)


# Singleton instance
_default_folder = HIPIFFolder()


def fold_completed_milestone(
    blueprint: TaskBlueprint,
    milestone_id: str,
    summary: Optional[str] = None,
    artifacts: Optional[List[str]] = None,
) -> StateCheckpoint:
    return _default_folder.fold_milestone(blueprint, milestone_id, summary=summary, artifacts=artifacts)
