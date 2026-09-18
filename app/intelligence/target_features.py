"""
app/intelligence/target_features.py

Feature representation for a UI element candidate.

CandidateFeatures captures the signals used to rank competing
UI element candidates for a given target query. The initial
implementation is fully deterministic and learning-ready.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CandidateFeatures:
    """
    Feature vector for one UI element candidate.
    """

    element_id: str = ""

    # Textual similarity
    text_similarity: float = 0.0
    description_similarity: float = 0.0

    # Perception confidence signals
    ocr_confidence: float = 0.0
    vlm_confidence: float = 0.0
    element_confidence: float = 0.0

    # Structural signals
    element_type_match: float = 0.0
    screen_region: str | None = None
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

    # Group / ordinal
    ordinal_rank: int | None = None
    group_match: float = 0.0

    # Historical
    historical_success_rate: float = 0.0

    # Spatial reasoning result
    spatial_score: float = 0.0

    # Foreground & Interactability
    foreground_match: float = 0.0
    interactability: float = 1.0

    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @property
    def combined_text_score(self) -> float:
        """Weighted combination of text and description similarity."""
        return max(
            self.text_similarity,
            self.description_similarity * 0.9,
        )

    @property
    def combined_confidence(self) -> float:
        """Best available perception confidence."""
        confidences = [
            c
            for c in (
                self.ocr_confidence,
                self.vlm_confidence,
                self.element_confidence,
            )
            if c > 0.0
        ]
        return max(confidences) if confidences else 0.0
