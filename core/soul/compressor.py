"""
Project Extra — Project SOUL (System One Ultra-fast Layer)
SOUL-Compressor: Semantic State Tokenizer & Context Folding Engine.
Compresses messy visual and physical desktop states into dense 10-15 word tokens.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional
from PIL import Image

from extra.core.soul.critic import CriticVerdict

logger = logging.getLogger("Extra-SOUL-Compressor")


class SoulCompressor:
    """
    Transforms multi-megabyte screenshots and verbose terminal logs into
    compact semantic tokens to protect LLM context windows against epistemic drift.
    """

    def compress_milestone_state(
        self,
        milestone_id: str,
        milestone_name: str,
        verdict: Optional[CriticVerdict] = None,
        artifacts: Optional[List[str]] = None,
        duration_ms: Optional[float] = None,
    ) -> str:
        """
        Creates a dense state token:
        e.g. `[STATE: M1_PASS | Name: 'Render 3D Mesh' | Arts: 2 | Latency: 120ms]`
        """
        status_tag = "PASS" if (verdict is None or verdict.passed) else "FAIL"
        art_count = len(artifacts) if artifacts else 0
        lat_str = f" | Latency: {int(duration_ms)}ms" if duration_ms is not None else ""

        token = f"[STATE: {milestone_id}_{status_tag} | Name: '{milestone_name}' | Artifacts: {art_count}{lat_str}]"
        logger.debug("[SOUL-Compressor] Generated state token: %s", token)
        return token


_default_compressor = SoulCompressor()


def compress_milestone_state(
    milestone_id: str,
    milestone_name: str,
    verdict: Optional[CriticVerdict] = None,
    artifacts: Optional[List[str]] = None,
) -> str:
    return _default_compressor.compress_milestone_state(
        milestone_id,
        milestone_name,
        verdict=verdict,
        artifacts=artifacts,
    )
