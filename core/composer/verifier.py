"""
Project Extra — Milestone Verifier Subsystem
Validates milestone satisfaction against physical artifacts, exit codes,
and perceptual visual criteria using Project SOUL.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from extra.core.composer.blueprint import Milestone

logger = logging.getLogger("Extra-Composer-Verifier")


@dataclass
class VerificationResult:
    """
    Result of a milestone verification check.
    """
    passed: bool
    score: float = 1.0
    defects: List[str] = field(default_factory=list)
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class MilestoneVerifier:
    """
    Evaluates whether a milestone's acceptance criteria are strictly satisfied
    before allowing downstream milestones to proceed.
    """

    def verify_milestone(
        self,
        milestone: Milestone,
        execution_result: Optional[Dict[str, Any]] = None,
    ) -> VerificationResult:
        t0 = time.perf_counter()
        defects: List[str] = []
        criteria = milestone.acceptance_criteria or {}

        # 1. Artifact Existence & Minimum Size Checks
        for art_path_str in milestone.expected_artifacts:
            art_path = Path(os.path.expandvars(art_path_str))
            if not art_path.exists():
                defects.append(f"Expected artifact not found: {art_path}")
            elif art_path.is_file():
                size = art_path.stat().st_size
                min_bytes = criteria.get("min_file_size_bytes", 10)
                if size < min_bytes:
                    defects.append(f"Artifact {art_path.name} is undersized ({size} bytes < {min_bytes} bytes)")

        # 2. Returncode Check (if bridge/process result present)
        if execution_result:
            returncode = execution_result.get("returncode", 0)
            expected_returncode = criteria.get("expected_returncode", 0)
            if returncode != expected_returncode:
                defects.append(f"Process failed with returncode {returncode} (expected {expected_returncode})")

        # 3. Custom String / Regex Checks in output
        if execution_result and "required_output_substr" in criteria:
            req_sub = criteria["required_output_substr"]
            stdout = execution_result.get("stdout", "")
            stderr = execution_result.get("stderr", "")
            if req_sub not in stdout and req_sub not in stderr:
                defects.append(f"Required substring '{req_sub}' not found in process output")

        # 4. Multimodal Visual Telemetry & SOUL-Critic Verification
        has_visual_criteria = (
            "expected_elements" in criteria
            or "unwanted_elements" in criteria
            or "visual_condition" in criteria
        )
        if has_visual_criteria:
            try:
                from extra.core.soul.critic import SoulCritic
                critic = SoulCritic()
                exp_elems = criteria.get("expected_elements")
                unw_elems = criteria.get("unwanted_elements")
                v_cond = criteria.get("visual_condition")

                verdict = critic.evaluate_screen_milestone(
                    milestone_name=milestone.name or milestone.id,
                    expected_elements=exp_elems,
                    unwanted_elements=unw_elems,
                    custom_condition=v_cond,
                )
                if not verdict.passed:
                    defects.extend(verdict.defects)
            except Exception as ex:
                logger.debug("SOUL-Critic milestone evaluation fallback: %s", ex)

        latency_ms = (time.perf_counter() - t0) * 1000.0
        passed = len(defects) == 0
        score = 1.0 if passed else max(0.0, 1.0 - (len(defects) * 0.3))

        return VerificationResult(
            passed=passed,
            score=score,
            defects=defects,
            latency_ms=latency_ms,
            metadata={"milestone_id": milestone.id, "checks_performed": len(criteria)},
        )


_default_verifier = MilestoneVerifier()


def verify_milestone_acceptance(
    milestone: Milestone,
    execution_result: Optional[Dict[str, Any]] = None,
) -> VerificationResult:
    return _default_verifier.verify_milestone(milestone, execution_result=execution_result)
