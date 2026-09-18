"""
app/intelligence/target_ranker.py

Deterministic weighted candidate ranker with ambiguity detection.

The TargetRanker takes a list of UIElement candidates and a TargetQuery,
extracts CandidateFeatures for each element, applies a weighted scoring
function, and returns a ranked list of RankedCandidate objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.intelligence.target_features import CandidateFeatures
from app.perception.ui_element import UIElement


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class RankedCandidate:
    """One scored, ranked UI element candidate."""

    element: UIElement
    features: CandidateFeatures
    score: float
    rank: int = 0
    reason: str = ""
    is_ambiguous: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AmbiguityResult:
    """Detailed ambiguity diagnostics when multiple candidates match with similar scores."""

    is_ambiguous: bool
    candidates: list[RankedCandidate] = field(default_factory=list)
    scores: list[float] = field(default_factory=list)
    confidence: float = 0.0
    reason: str = ""
    clarification_question: str = ""


@dataclass
class RankingResult:
    """The result of a ranking operation."""

    candidates: list[RankedCandidate] = field(default_factory=list)
    best: RankedCandidate | None = None
    is_ambiguous: bool = False
    reason: str = ""
    ambiguity_result: AmbiguityResult | None = None

    @property
    def found(self) -> bool:
        return self.best is not None and not self.is_ambiguous


# ---------------------------------------------------------------------------
# Default weights & thresholds
# ---------------------------------------------------------------------------


DEFAULT_WEIGHTS: dict[str, float] = {
    "text_similarity": 0.35,
    "description_similarity": 0.10,
    "element_confidence": 0.10,
    "spatial_score": 0.15,
    "group_match": 0.10,
    "element_type": 0.05,
    "foreground_match": 0.05,
    "interactability": 0.05,
    "historical_success_rate": 0.05,
}

MINIMUM_SCORE_THRESHOLD = 0.35
AMBIGUITY_MARGIN = 0.12


# ---------------------------------------------------------------------------
# Feature extractor
# ---------------------------------------------------------------------------


class FeatureExtractor:
    """
    Extracts CandidateFeatures from a UIElement given a TargetQuery.
    """

    def extract(
        self,
        element: UIElement,
        query,
        history=None,
        foreground_context=None,
    ) -> CandidateFeatures:
        features = CandidateFeatures(
            element_id=element.element_id,
            x=element.x,
            y=element.y,
            width=element.width,
            height=element.height,
            ocr_confidence=(
                element.confidence
                if getattr(element, "source", "") in ("OCR", "FUSED", "unknown")
                else 0.0
            ),
            vlm_confidence=(
                element.confidence
                if getattr(element, "source", "") in ("VLM", "FUSED")
                else 0.0
            ),
            element_confidence=element.confidence,
            interactability=1.0 if element.is_interactable else 0.3,
        )

        # Text similarity
        if query and query.text:
            features.text_similarity = self._text_similarity(
                element.text,
                query.text,
            )
            features.description_similarity = self._text_similarity(
                element.description,
                query.text,
            )

        # Element type match
        if query and query.element_type:
            features.element_type_match = (
                1.0
                if (element.element_type or "").lower() == query.element_type.lower()
                else 0.0
            )

        # Group / semantic role match
        if query and query.group:
            elem_group = getattr(element, "group", None) or getattr(element, "semantic_role", None)
            features.group_match = (
                1.0
                if elem_group and query.group.lower() in elem_group.lower()
                else 0.0
            )

        # Foreground application match
        if foreground_context:
            app_name = getattr(element, "app_name", None) or getattr(element, "window_title", None)
            if app_name and hasattr(foreground_context, "matches"):
                features.foreground_match = 1.0 if foreground_context.matches(app_name) else 0.0
            elif hasattr(foreground_context, "app_name") and app_name:
                features.foreground_match = 1.0 if app_name.lower() in foreground_context.app_name.lower() else 0.0

        # Historical success
        if history and element.text:
            features.historical_success_rate = history.success_rate(element.text)

        return features

    @staticmethod
    def _text_similarity(a: str | None, b: str | None) -> float:
        if not a or not b:
            return 0.0
        norm_a = " ".join(a.strip().lower().split())
        norm_b = " ".join(b.strip().lower().split())
        if norm_a == norm_b:
            return 1.0
        if norm_a in norm_b or norm_b in norm_a:
            return 0.85
        words_a = set(norm_a.split())
        words_b = set(norm_b.split())
        if not words_a or not words_b:
            return 0.0
        return len(words_a & words_b) / len(words_a | words_b)


# ---------------------------------------------------------------------------
# TargetRanker
# ---------------------------------------------------------------------------


class TargetRanker:
    """
    Ranks UIElement candidates against a TargetQuery and detects ambiguity.
    """

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        min_score: float = MINIMUM_SCORE_THRESHOLD,
        ambiguity_margin: float = AMBIGUITY_MARGIN,
        history=None,
    ):
        self.weights = weights or dict(DEFAULT_WEIGHTS)
        self.min_score = min_score
        self.ambiguity_margin = ambiguity_margin
        self.history = history
        self._extractor = FeatureExtractor()

    def rank(
        self,
        elements: list[UIElement],
        query=None,
        spatial_scores: dict[str, float] | None = None,
        foreground_context=None,
    ) -> RankingResult:
        if not elements:
            return RankingResult(reason="No candidate elements provided.")

        spatial = spatial_scores or {}
        scored: list[RankedCandidate] = []

        for element in elements:
            features = self._extractor.extract(
                element, query, self.history, foreground_context=foreground_context
            )
            if element.element_id in spatial:
                features.spatial_score = spatial[element.element_id]

            score = self._compute_score(features)
            reason_parts = self._explain(features, score)

            scored.append(
                RankedCandidate(
                    element=element,
                    features=features,
                    score=score,
                    reason=reason_parts,
                )
            )

        scored.sort(key=lambda c: c.score, reverse=True)

        for i, candidate in enumerate(scored):
            candidate.rank = i + 1

        qualifying = [c for c in scored if c.score >= self.min_score]

        if not qualifying:
            return RankingResult(
                candidates=scored,
                reason=(
                    f"No candidate reached minimum score threshold ({self.min_score:.2f}). "
                    f"Best was {scored[0].score:.2f} for '{scored[0].element.text or scored[0].element.element_id}'."
                ),
            )

        best = qualifying[0]
        is_ambiguous = False
        ambiguity_res = None

        if len(qualifying) >= 2:
            second_score = qualifying[1].score
            diff = best.score - second_score
            if diff < self.ambiguity_margin:
                is_ambiguous = True
                best.is_ambiguous = True
                qualifying[1].is_ambiguous = True

                competing = [best, qualifying[1]]
                q_text = query.text if query and query.text else "target"
                clarification = self._generate_clarification_question(q_text, competing)

                ambiguity_res = AmbiguityResult(
                    is_ambiguous=True,
                    candidates=competing,
                    scores=[best.score, second_score],
                    confidence=round(best.score, 2),
                    reason=f"Ambiguity detected: top 2 candidates have close scores ({best.score:.2f} vs {second_score:.2f}, margin {diff:.2f} < {self.ambiguity_margin:.2f}).",
                    clarification_question=clarification,
                )

        return RankingResult(
            candidates=scored,
            best=best,
            is_ambiguous=is_ambiguous,
            reason=best.reason,
            ambiguity_result=ambiguity_res,
        )

    def check_ambiguity(
        self,
        elements: list[UIElement],
        query=None,
        spatial_scores: dict[str, float] | None = None,
        foreground_context=None,
    ) -> AmbiguityResult:
        """Check whether ranking elements for query yields an ambiguous result."""
        result = self.rank(
            elements=elements,
            query=query,
            spatial_scores=spatial_scores,
            foreground_context=foreground_context,
        )
        if result.ambiguity_result:
            return result.ambiguity_result
        return AmbiguityResult(
            is_ambiguous=False,
            candidates=result.candidates[:1] if result.candidates else [],
            scores=[result.candidates[0].score] if result.candidates else [],
            confidence=result.candidates[0].score if result.candidates else 0.0,
            reason=result.reason,
        )

    def _compute_score(self, features: CandidateFeatures) -> float:
        w = self.weights
        score = (
            w.get("text_similarity", 0.35) * features.text_similarity
            + w.get("description_similarity", 0.10) * features.description_similarity
            + w.get("element_confidence", 0.10) * features.element_confidence
            + w.get("spatial_score", 0.15) * features.spatial_score
            + w.get("group_match", 0.10) * features.group_match
            + w.get("element_type", 0.05) * features.element_type_match
            + w.get("foreground_match", 0.05) * features.foreground_match
            + w.get("interactability", 0.05) * features.interactability
            + w.get("historical_success_rate", 0.05) * features.historical_success_rate
        )
        return max(0.0, min(1.0, score))

    @staticmethod
    def _generate_clarification_question(
        target_name: str,
        competing: list[RankedCandidate],
    ) -> str:
        descriptions = []
        for i, c in enumerate(competing[:2]):
            elem = c.element
            loc = "top" if elem.y < 300 else ("bottom" if elem.y > 600 else "middle")
            desc = f"{elem.element_type} near the {loc}"
            if elem.app_name:
                desc += f" in {elem.app_name}"
            descriptions.append(desc)

        return f"I found multiple elements matching '{target_name}'. Did you mean the {descriptions[0]} or the {descriptions[1]}?"

    @staticmethod
    def _explain(features: CandidateFeatures, score: float) -> str:
        parts: list[str] = []
        if features.text_similarity >= 0.9:
            parts.append("exact text match")
        elif features.text_similarity >= 0.5:
            parts.append(f"text similarity {features.text_similarity:.2f}")

        if features.description_similarity >= 0.7:
            parts.append("description match")

        if features.spatial_score >= 0.8:
            parts.append("strong spatial match")
        elif features.spatial_score >= 0.3:
            parts.append(f"spatial score {features.spatial_score:.2f}")

        if features.group_match >= 1.0:
            parts.append("group match")

        if features.foreground_match >= 1.0:
            parts.append("foreground app match")

        explanation = "; ".join(parts) if parts else "best available match"
        return f"score={score:.2f} ({explanation})"
