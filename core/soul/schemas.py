"""
Project Extra — Project SOUL (System One Ultra-fast Layer)
Schemas and typed data structures for local reflex micro-decisions and visual grounding.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union


class DecisionType(str, Enum):
    BOOLEAN = "boolean"
    CHOICE = "choice"
    SCORE = "score"
    CLASSIFY = "classify"


@dataclass
class SoulDecision:
    """
    Structured outcome of a SOUL reflex decision.
    Mathematically typed with confidence score and latency benchmark.
    """
    decision_type: DecisionType
    result: Union[bool, str, float, int]
    confidence: float
    latency_ms: float
    model_name: str
    raw_output: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_confident(self) -> bool:
        """Returns True if the confidence meets or exceeds the default 0.70 threshold."""
        return self.confidence >= 0.70

    def as_dict(self) -> Dict[str, Any]:
        return {
            "decision_type": self.decision_type.value,
            "result": self.result,
            "confidence": round(self.confidence, 4),
            "latency_ms": round(self.latency_ms, 2),
            "model_name": self.model_name,
            "raw_output": self.raw_output,
            "metadata": self.metadata,
        }


@dataclass
class SoulBoundingBox:
    """
    Normalized [ymin, xmin, ymax, xmax] bounding box in [0.0, 1000.0] coordinate space.
    Compatible with extra.core.geometry for PerMonitorV2 physical monitor mapping.
    """
    ymin: float
    xmin: float
    ymax: float
    xmax: float
    label: str = ""
    confidence: float = 1.0

    @property
    def center(self) -> Tuple[float, float]:
        """Returns normalized (center_x, center_y) in [0, 1000] space."""
        return ((self.xmin + self.xmax) / 2.0, (self.ymin + self.ymax) / 2.0)

    @property
    def width(self) -> float:
        return max(0.0, self.xmax - self.xmin)

    @property
    def height(self) -> float:
        return max(0.0, self.ymax - self.ymin)


@dataclass
class GroundingResult:
    """Result of an on-demand SOUL visual grounding operation."""
    query: str
    matched: bool
    bounding_box: Optional[SoulBoundingBox]
    latency_ms: float
    screen_point: Optional[Tuple[int, int]] = None  # Physical screen (x, y) if denormalized
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def confidence(self) -> float:
        return self.bounding_box.confidence if self.bounding_box is not None else (1.0 if self.matched else 0.0)
