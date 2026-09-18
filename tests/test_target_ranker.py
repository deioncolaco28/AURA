"""Tests for TargetRanker and CandidateFeatures."""

import pytest

from app.intelligence.interaction_history import InteractionHistory
from app.intelligence.target_features import CandidateFeatures
from app.intelligence.target_ranker import (
    AMBIGUITY_MARGIN,
    DEFAULT_WEIGHTS,
    FeatureExtractor,
    RankedCandidate,
    RankingResult,
    TargetRanker,
)
from app.perception.target_query import TargetQuery
from app.perception.ui_element import UIElement


def make_element(eid, text, confidence=0.9, description=None):
    return UIElement(
        element_id=eid,
        element_type="button",
        text=text,
        description=description,
        x=100,
        y=100,
        width=100,
        height=30,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# CandidateFeatures
# ---------------------------------------------------------------------------


class TestCandidateFeatures:

    def test_combined_text_score_prefers_text(self):
        f = CandidateFeatures(
            text_similarity=0.9,
            description_similarity=0.5,
        )
        assert f.combined_text_score == 0.9

    def test_combined_text_score_uses_description_when_higher(self):
        f = CandidateFeatures(
            text_similarity=0.2,
            description_similarity=0.8,
        )
        # description_similarity * 0.9 = 0.72 > text_similarity 0.2
        assert f.combined_text_score == pytest.approx(0.72)

    def test_combined_confidence_uses_best(self):
        f = CandidateFeatures(
            ocr_confidence=0.7,
            vlm_confidence=0.9,
            element_confidence=0.5,
        )
        assert f.combined_confidence == 0.9

    def test_combined_confidence_zero_when_all_zero(self):
        f = CandidateFeatures()
        assert f.combined_confidence == 0.0


# ---------------------------------------------------------------------------
# FeatureExtractor
# ---------------------------------------------------------------------------


class TestFeatureExtractor:

    def test_exact_text_match(self):
        extractor = FeatureExtractor()
        elem = make_element("1", "Notepad")
        query = TargetQuery(text="Notepad")
        features = extractor.extract(elem, query)
        assert features.text_similarity == 1.0

    def test_case_insensitive_text_match(self):
        extractor = FeatureExtractor()
        elem = make_element("1", "notepad")
        query = TargetQuery(text="Notepad")
        features = extractor.extract(elem, query)
        assert features.text_similarity == 1.0

    def test_partial_text_match(self):
        extractor = FeatureExtractor()
        elem = make_element("1", "Notepad application")
        query = TargetQuery(text="Notepad")
        features = extractor.extract(elem, query)
        # "Notepad" is contained within "Notepad application",
        # so we get a partial-containment score > 0 and < 1.
        assert 0.0 < features.text_similarity < 1.0

    def test_no_text_query_zero_similarity(self):
        extractor = FeatureExtractor()
        elem = make_element("1", "Notepad")
        query = TargetQuery()  # no text
        features = extractor.extract(elem, query)
        assert features.text_similarity == 0.0

    def test_element_type_match(self):
        extractor = FeatureExtractor()
        elem = make_element("1", "Submit")
        query = TargetQuery(element_type="button")
        features = extractor.extract(elem, query)
        assert features.element_type_match == 1.0

    def test_element_type_mismatch(self):
        extractor = FeatureExtractor()
        elem = UIElement(
            element_id="1",
            element_type="input",
            text="Search",
        )
        query = TargetQuery(element_type="button")
        features = extractor.extract(elem, query)
        assert features.element_type_match == 0.0

    def test_historical_success_rate_from_history(self):
        extractor = FeatureExtractor()
        history = InteractionHistory()
        history.record(
            target="notepad",
            element_text="notepad",
            verification_result="success",
        )
        elem = make_element("1", "Notepad")
        query = TargetQuery(text="Notepad")
        features = extractor.extract(elem, query, history=history)
        assert features.historical_success_rate == 1.0


# ---------------------------------------------------------------------------
# TargetRanker — basic ranking
# ---------------------------------------------------------------------------


class TestTargetRanker:

    def test_exact_match_ranks_first(self):
        ranker = TargetRanker()
        exact = make_element("1", "Notepad", confidence=0.9)
        partial = make_element("2", "Notepad application", confidence=0.9)
        query = TargetQuery(text="Notepad")
        result = ranker.rank([partial, exact], query)
        assert result.best is not None
        assert result.best.element.element_id == "1"

    def test_no_candidates_returns_no_best(self):
        ranker = TargetRanker()
        result = ranker.rank([], TargetQuery(text="Notepad"))
        assert result.best is None
        assert not result.found

    def test_result_has_ranked_candidates(self):
        ranker = TargetRanker()
        a = make_element("1", "Notepad")
        b = make_element("2", "Calculator")
        query = TargetQuery(text="Notepad")
        result = ranker.rank([a, b], query)
        assert len(result.candidates) == 2
        assert result.candidates[0].rank == 1
        assert result.candidates[1].rank == 2

    def test_below_threshold_no_best(self):
        ranker = TargetRanker(min_score=0.99)  # very high threshold
        elem = make_element("1", "Something", confidence=0.1)
        query = TargetQuery(text="CompletelyDifferent")
        result = ranker.rank([elem], query)
        assert result.best is None
        assert not result.found

    def test_deterministic_same_inputs_same_ranking(self):
        ranker = TargetRanker()
        elements = [
            make_element("1", "Notepad"),
            make_element("2", "Calculator"),
            make_element("3", "Paint"),
        ]
        query = TargetQuery(text="Notepad")
        result1 = ranker.rank(elements, query)
        result2 = ranker.rank(elements, query)
        assert result1.best.element.element_id == result2.best.element.element_id

    def test_reason_included_in_result(self):
        ranker = TargetRanker()
        elem = make_element("1", "Notepad", confidence=0.9)
        query = TargetQuery(text="Notepad")
        result = ranker.rank([elem], query)
        assert result.reason
        assert "score" in result.reason


# ---------------------------------------------------------------------------
# TargetRanker — ambiguity
# ---------------------------------------------------------------------------


class TestTargetRankerAmbiguity:

    def test_identical_candidates_are_ambiguous(self):
        """
        Two candidates with identical text and confidence → ambiguous.
        """
        ranker = TargetRanker()
        a = make_element("1", "Notepad", confidence=0.9)
        b = make_element("2", "Notepad", confidence=0.9)
        query = TargetQuery(text="Notepad")
        result = ranker.rank([a, b], query)
        # Both candidates produce the same score → within ambiguity margin
        assert result.is_ambiguous

    def test_clearly_better_candidate_not_ambiguous(self):
        """
        Strong exact match vs. completely different text → not ambiguous.
        """
        ranker = TargetRanker()
        strong = make_element("1", "Notepad", confidence=0.95)
        weak = make_element("2", "ZZZZZZZZ", confidence=0.1)
        query = TargetQuery(text="Notepad")
        result = ranker.rank([strong, weak], query)
        assert not result.is_ambiguous
        assert result.best.element.element_id == "1"

    def test_single_candidate_not_ambiguous(self):
        ranker = TargetRanker()
        elem = make_element("1", "Notepad", confidence=0.9)
        query = TargetQuery(text="Notepad")
        result = ranker.rank([elem], query)
        assert not result.is_ambiguous


# ---------------------------------------------------------------------------
# TargetRanker — spatial score injection
# ---------------------------------------------------------------------------


class TestTargetRankerSpatialScores:

    def test_spatial_score_affects_ranking(self):
        # Use a lower min_score so the spatial-only boost is sufficient.
        ranker = TargetRanker(min_score=0.1)
        a = make_element("1", "Item A", confidence=0.5)
        b = make_element("2", "Item B", confidence=0.5)
        query = TargetQuery(ordinal=1)

        # Give element "2" a high spatial score
        spatial_scores = {"2": 1.0, "1": 0.0}
        result = ranker.rank([a, b], query, spatial_scores=spatial_scores)
        assert result.best is not None
        assert result.best.element.element_id == "2"
