"""
app/intelligence/target_ranker.py

Deterministic weighted candidate ranker.

The TargetRanker takes a list of UIElement candidates and a TargetQuery,
extracts CandidateFeatures for each element, applies a weighted scoring
function, and returns a ranked list of RankedCandidate objects.

The architecture is learning-ready: an InteractionHistory can be injected
to influence historical_success_rate scores.

Design principles
-----------------
- Deterministic: same inputs always produce the same ranking.
- Explainable: each RankedCandidate includes a reason string.
- Ambiguity-aware: when two candidates are too close in score the ranker
  reports ambiguity rather than fabricating certainty.
- No application-specific hard-coding.
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
class RankingResult:
    """The result of a ranking operation."""

    candidates: list[RankedCandidate] = field(default_factory=list)
    best: RankedCandidate | None = None
    is_ambiguous: bool = False
    reason: str = ""

    @property
    def found(self) -> bool:
        return self.best is not None and not self.is_ambiguous


# ---------------------------------------------------------------------------
# Default weights
# ---------------------------------------------------------------------------


DEFAULT_WEIGHTS: dict[str, float] = {
    "text_similarity": 0.40,
    "description_similarity": 0.10,
    "element_confidence": 0.15,
    "spatial_score": 0.20,
    "group_match": 0.10,
    "historical_success_rate": 0.05,
}

# Minimum score for a candidate to be considered.
MINIMUM_SCORE_THRESHOLD = 0.35

# If the top two candidates are within this margin, report ambiguity.
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
    ) -> CandidateFeatures:
        """
        Extract a feature vector for one candidate element.

        Parameters
        ----------
        element : UIElement
        query : TargetQuery
        history : InteractionHistory | None
        """

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
        )

        # ----------------------------------------------------------
        # Text similarity
        # ----------------------------------------------------------
        if query and query.text:
            features.text_similarity = self._text_similarity(
                element.text,
                query.text,
            )
            features.description_similarity = self._text_similarity(
                element.description,
                query.text,
            )

        # ----------------------------------------------------------
        # Element type match
        # ----------------------------------------------------------
        if query and query.element_type:
            if (
                str(element.element_type).lower()
                == query.element_type.lower()
            ):
                features.element_type_match = 1.0

        # ----------------------------------------------------------
        # Group match
        # ----------------------------------------------------------
        if query and query.group:
            g = query.group.lower()
            if (
                str(getattr(element, "group", "") or "").lower() == g
                or str(
                    getattr(element, "semantic_role", "") or ""
                ).lower() == g
            ):
                features.group_match = 1.0

        # ----------------------------------------------------------
        # Historical success rate
        # ----------------------------------------------------------
        if history:
            label = self._element_label(element)
            features.historical_success_rate = (
                history.success_rate(label)
            )

        return features

    @staticmethod
    def _text_similarity(
        candidate_text: str | None,
        query_text: str,
    ) -> float:
        """Simple normalised text similarity."""

        if not candidate_text or not query_text:
            return 0.0

        c = candidate_text.strip().lower()
        q = query_text.strip().lower()

        if not c or not q:
            return 0.0

        # Exact match
        if c == q:
            return 1.0

        # Case-insensitive full containment
        if q in c or c in q:
            shorter = min(len(c), len(q))
            longer = max(len(c), len(q))
            return 0.85 * shorter / longer

        # Token overlap (Jaccard)
        c_tokens = set(c.split())
        q_tokens = set(q.split())

        if not c_tokens or not q_tokens:
            return 0.0

        intersection = c_tokens & q_tokens
        union = c_tokens | q_tokens

        return 0.7 * len(intersection) / len(union)

    @staticmethod
    def _element_label(element: UIElement) -> str:
        return (
            str(element.text or "").strip().lower()
            or element.element_id
        )


# ---------------------------------------------------------------------------
# TargetRanker
# ---------------------------------------------------------------------------


class TargetRanker:
    """
    Ranks UIElement candidates for a TargetQuery.

    Usage
    -----
    ::

        ranker = TargetRanker()
        result = ranker.rank(elements, query, spatial_scores)
    """

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        min_score: float = MINIMUM_SCORE_THRESHOLD,
        ambiguity_margin: float = AMBIGUITY_MARGIN,
        history=None,
    ):
        self.weights = weights or DEFAULT_WEIGHTS
        self.min_score = min_score
        self.ambiguity_margin = ambiguity_margin
        self.history = history  # InteractionHistory | None
        self._extractor = FeatureExtractor()

    def rank(
        self,
        elements: list[UIElement],
        query=None,
        spatial_scores: dict[str, float] | None = None,
    ) -> RankingResult:
        """
        Rank candidates and return a RankingResult.

        Parameters
        ----------
        elements : list[UIElement]
            Candidate elements.
        query : TargetQuery | None
            The structured target request. When None, elements are ranked
            by element_confidence alone.
        spatial_scores : dict[str, float] | None
            Optional spatial scores keyed by element_id (from SpatialReasoner).

        Returns
        -------
        RankingResult
        """

        if not elements:
            return RankingResult(
                reason="No candidate elements provided."
            )

        spatial = spatial_scores or {}

        scored: list[RankedCandidate] = []

        for element in elements:
            features = self._extractor.extract(
                element, query, self.history
            )

            # Inject spatial score from external resolver.
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

        # Sort descending by score.
        scored.sort(key=lambda c: c.score, reverse=True)

        # Assign ranks.
        for i, candidate in enumerate(scored):
            candidate.rank = i + 1

        # Filter below minimum threshold.
        qualifying = [c for c in scored if c.score >= self.min_score]

        if not qualifying:
            return RankingResult(
                candidates=scored,
                reason=(
                    f"No candidate reached minimum score threshold "
                    f"({self.min_score:.2f}). "
                    f"Best was {scored[0].score:.2f} for "
                    f"'{scored[0].element.text or scored[0].element.element_id}'."
                ),
            )

        best = qualifying[0]

        # Ambiguity check: are the top two candidates too close?
        is_ambiguous = False

        if len(qualifying) >= 2:
            second_score = qualifying[1].score

            if best.score - second_score < self.ambiguity_margin:
                is_ambiguous = True
                best.is_ambiguous = True
                qualifying[1].is_ambiguous = True

        return RankingResult(
            candidates=scored,
            best=best,
            is_ambiguous=is_ambiguous,
            reason=best.reason,
        )

    def _compute_score(
        self,
        features: CandidateFeatures,
    ) -> float:
        """Weighted dot product of feature values."""

        w = self.weights

        score = (
            w.get("text_similarity", 0.0)
            * features.text_similarity
            + w.get("description_similarity", 0.0)
            * features.description_similarity
            + w.get("element_confidence", 0.0)
            * features.element_confidence
            + w.get("spatial_score", 0.0)
            * features.spatial_score
            + w.get("group_match", 0.0)
            * features.group_match
            + w.get("historical_success_rate", 0.0)
            * features.historical_success_rate
        )

        # Clamp to [0, 1].
        return max(0.0, min(1.0, score))

    @staticmethod
    def _explain(
        features: CandidateFeatures,
        score: float,
    ) -> str:
        """Generate a human-readable explanation of the ranking."""

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

        if features.historical_success_rate >= 0.7:
            parts.append(
                f"historical success {features.historical_success_rate:.0%}"
            )

        explanation = "; ".join(parts) if parts else "best available match"
        return f"score={score:.2f} ({explanation})"
