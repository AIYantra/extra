"""
Project Extra — Project SOUL (System One Ultra-fast Layer)
SOUL-Critic: On-Device Milestone Acceptance & Defect Evaluation Head.
Evaluates local visual fidelity, error states, and milestone completion without cloud roundtrips.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from PIL import Image

from extra.core.capture import capture_screen
from extra.core.soul.decider import SoulDecider
from extra.core.soul.eyes import SoulEyes

logger = logging.getLogger("Extra-SOUL-Critic")


@dataclass
class CriticVerdict:
    """
    Evaluation verdict from SOUL-Critic.
    """
    passed: bool
    confidence: float
    defects: List[str] = field(default_factory=list)
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class SoulCritic:
    """
    Local visual quality and milestone acceptance evaluator.
    Combines SOUL-Eyes visual grounding and SOUL-Decider reflexive classification.
    """

    def __init__(self) -> None:
        self.decider = SoulDecider()
        self.eyes = SoulEyes()

    def evaluate_screen_milestone(
        self,
        milestone_name: str,
        expected_elements: Optional[List[str]] = None,
        unwanted_elements: Optional[List[str]] = None,
        custom_condition: Optional[str] = None,
        image: Optional[Image.Image] = None,
        monitor_index: int = 0,
    ) -> CriticVerdict:
        """
        Evaluates active screen state against milestone expectations.
        """
        t0 = time.perf_counter()
        target_img = image or capture_screen(monitor_index).image
        defects: List[str] = []
        confidences: List[float] = []

        # 1. Check for presence of required visual elements
        if expected_elements:
            for elem in expected_elements:
                res = self.eyes.visual_ground(image=target_img, query=elem)
                is_generic_fallback = (
                    res.bounding_box is not None
                    and res.bounding_box.label == "center_canvas"
                    and "canvas" not in elem.lower()
                )
                if not res.matched or is_generic_fallback or res.confidence < 0.75:
                    defects.append(f"Required element '{elem}' not found on screen")
                    confidences.append(0.2)
                else:
                    confidences.append(res.confidence)

        # 2. Check for absence of unwanted elements (error dialogs, crash modals)
        unwanted = unwanted_elements or ["Error", "Crash", "Unresponsive"]
        for bad_elem in unwanted:
            res = self.eyes.visual_ground(image=target_img, query=bad_elem)
            if res.matched and res.confidence >= 0.80:
                defects.append(f"Unwanted state or error modal detected: '{bad_elem}'")
                confidences.append(0.1)

        # 3. Custom condition evaluation via SOUL-Decider
        if custom_condition:
            dec = self.decider.decide_boolean(custom_condition, context={"milestone": milestone_name})
            confidences.append(dec.confidence)
            if not dec.result:
                defects.append(f"Custom visual condition failed: '{custom_condition}'")

        latency_ms = (time.perf_counter() - t0) * 1000.0
        passed = len(defects) == 0
        overall_conf = (sum(confidences) / len(confidences)) if confidences else (1.0 if passed else 0.0)

        logger.info(
            "[SOUL-Critic] Milestone '%s' -> %s (conf: %.2f, %d defects in %.1fms)",
            milestone_name, "PASSED" if passed else "FAILED", overall_conf, len(defects), latency_ms
        )

        return CriticVerdict(
            passed=passed,
            confidence=round(overall_conf, 3),
            defects=defects,
            latency_ms=round(latency_ms, 2),
            metadata={"milestone": milestone_name},
        )


_default_critic = SoulCritic()


def evaluate_screen_milestone(
    milestone_name: str,
    expected_elements: Optional[List[str]] = None,
    custom_condition: Optional[str] = None,
) -> CriticVerdict:
    return _default_critic.evaluate_screen_milestone(
        milestone_name,
        expected_elements=expected_elements,
        custom_condition=custom_condition,
    )
