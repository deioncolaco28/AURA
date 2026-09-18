"""
Tests for Phase 2: Computer Perception & UI Understanding.

Covers:
1. UIElement: Stable IDs, bounding boxes, interactability, similarity.
2. Accessibility Providers: MockAccessibilityProvider, DOMAccessibilityProvider, WindowsAccessibilityProvider.
3. UIElementGraph: Hierarchy tree, spatial neighborhood, query helpers.
4. PerceptionCache: Fingerprinting, hits, invalidation, TTL expiry.
5. ForegroundApplicationDetector & ApplicationContext.
6. Multi-Source PerceptionManager: Fusion, deduplication, degradation.
7. Expanded SpatialReasoner: Axis ordinals, between, inside, beside, nearest.
8. TargetQuery: Directional ordinals, relational query parsing.
9. TargetRanker: AmbiguityResult, multi-candidate ties, clarification questions.
10. ScrollPerceptionHandler: Bounded scroll-search loops, end-of-content detection.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch
import pytest

from app.perception.config import PerceptionConfig
from app.perception.errors import (
    ApplicationNotForegroundError,
    PerceptionError,
    ScrollLimitReachedError,
    TargetAmbiguousError,
    TargetNotFoundError,
)
from app.perception.ui_element import UIElement, generate_stable_id
from app.perception.ui_graph import UIElementGraph
from app.perception.accessibility import (
    AccessibilityProvider,
    DOMAccessibilityProvider,
    MockAccessibilityProvider,
    WindowsAccessibilityProvider,
)
from app.perception.cache import PerceptionCache
from app.perception.foreground_detector import (
    ApplicationContext,
    ForegroundApplicationDetector,
)
from app.perception.perception_manager import PerceptionManager
from app.perception.perception_result import PerceptionResult
from app.perception.spatial_reasoner import SpatialReasoner, SpatialResult
from app.perception.target_query import TargetQuery, parse_target_query
from app.perception.scroll_handler import ScrollPerceptionHandler
from app.intelligence.target_ranker import AmbiguityResult, TargetRanker
from app.core.observation import ScreenObservation
from app.core.observation_diff import ObservationDiff, diff_observations


# ==============================================================================
# 1. UIElement Tests
# ==============================================================================

class TestUIElementPhase2:
    def test_stable_id_deterministic(self):
        id1 = generate_stable_id("button", "Submit", 100, 200, 80, 30, source="chrome")
        id2 = generate_stable_id("button", "Submit", 100, 200, 80, 30, source="chrome")
        assert id1 == id2
        assert "button" in id1
        assert "submit" in id1

    def test_stable_id_geometry_grid_tolerance(self):
        # Coordinates within 10px quantize to same grid cell
        id1 = generate_stable_id("btn", "OK", 100, 100, 50, 20)
        id2 = generate_stable_id("btn", "OK", 104, 103, 50, 20)
        assert id1 == id2

    def test_ui_element_properties_and_bounds(self):
        elem = UIElement(
            element_id="btn_1",
            text="Save",
            element_type="button",
            x=100,
            y=200,
            width=100,
            height=40,
            confidence=0.95,
            source="accessibility",
            app_name="notepad",
        )
        assert elem.bounds == (100, 200, 100, 40)
        assert elem.area == 4000
        assert elem.center == (150, 220)
        assert elem.is_interactable is True
        assert elem.contains_point(150, 220) is True
        assert elem.contains_point(50, 50) is False
        assert elem.stable_id is not None

    def test_ui_element_similarity(self):
        elem1 = UIElement(element_id="1", text="Search", element_type="input", x=100, y=100, width=50, height=20)
        elem2 = UIElement(element_id="2", text="search", element_type="input", x=105, y=102, width=50, height=20)
        elem3 = UIElement(element_id="3", text="Cancel", element_type="button", x=500, y=500, width=50, height=20)

        assert elem1.is_similar_to(elem2, position_tolerance=20) is True
        assert elem1.is_similar_to(elem3) is False


# ==============================================================================
# 2. Accessibility Providers Tests
# ==============================================================================

class TestAccessibilityProviders:
    def test_mock_accessibility_provider(self):
        mock_elem = UIElement(
            element_id="btn_submit",
            text="Submit",
            element_type="button",
            x=100,
            y=200,
            width=80,
            height=30,
            source="accessibility",
        )
        provider = MockAccessibilityProvider(elements=[mock_elem])
        assert provider.is_available() is True
        elements = provider.capture()
        assert len(elements) == 1
        assert elements[0].text == "Submit"
        assert elements[0].element_type == "button"
        assert elements[0].source == "accessibility"

    def test_dom_accessibility_provider_extraction(self):
        mock_page = MagicMock()
        mock_page.is_closed.return_value = False
        mock_page.evaluate.return_value = [
            {"index": 0, "tag": "nav", "role": "navigation", "text": "", "x": 0, "y": 0, "width": 1920, "height": 60, "enabled": True},
            {"index": 1, "tag": "button", "role": "button", "text": "Log In", "x": 1800, "y": 15, "width": 80, "height": 30, "enabled": True},
        ]
        mock_browser = MagicMock()
        mock_browser.page = mock_page

        provider = DOMAccessibilityProvider(browser_controller=mock_browser)
        assert provider.is_available() is True
        elements = provider.capture()
        assert len(elements) == 2
        login_btn = next(e for e in elements if e.text == "Log In")
        assert login_btn.element_type == "button"
        assert login_btn.source == "DOM"

    def test_windows_provider_graceful_fallback(self):
        provider = WindowsAccessibilityProvider()
        elements = provider.capture()
        assert isinstance(elements, list)


# ==============================================================================
# 3. UIElementGraph Tests
# ==============================================================================

class TestUIElementGraph:
    def test_graph_hierarchy_and_queries(self):
        nav = UIElement(element_id="nav", text="Navigation", element_type="container", x=0, y=0, width=1000, height=60)
        btn1 = UIElement(element_id="home", text="Home", element_type="button", parent_id="nav", x=10, y=10, width=80, height=40)
        btn2 = UIElement(element_id="about", text="About", element_type="button", parent_id="nav", x=100, y=10, width=80, height=40)
        content = UIElement(element_id="body", text="Welcome", element_type="label", x=50, y=200, width=400, height=50)

        graph = UIElementGraph.build_from_elements([nav, btn1, btn2, content])

        assert len(graph.all_elements()) == 4
        parent = graph.get_parent("home")
        assert parent is not None
        assert parent.element_id == "nav"
        
        children = graph.get_children("nav")
        assert len(children) == 2
        assert {c.element_id for c in children} == {"home", "about"}

        siblings = graph.get_siblings("home")
        assert len(siblings) == 1
        assert siblings[0].element_id == "about"

        # Spatial neighbors
        neighbors = graph.get_spatial_neighbors("home", radius=100)
        assert any(n.element_id == "about" for n in neighbors)
        assert not any(n.element_id == "body" for n in neighbors)

        # Find helpers
        assert len(graph.find_by_type("button")) == 2
        assert len(graph.find_by_text("Home")) == 1


# ==============================================================================
# 4. PerceptionCache Tests
# ==============================================================================

class TestPerceptionCache:
    def test_cache_hit_and_invalidation(self):
        cache = PerceptionCache(ttl_seconds=1.0)
        elem = UIElement(element_id="btn", text="Click Me", element_type="button", x=100, y=100, width=50, height=20)
        res = PerceptionResult(elements=[elem], sources_used=["test"])

        raw_image = MagicMock()
        sig = cache.compute_signature(raw_image)
        cache.set(sig, res)

        cached = cache.get(sig)
        assert cached is not None
        assert cached.elements[0].text == "Click Me"

        # Explicit invalidation
        cache.invalidate("action_executed")
        assert cache.get(sig) is None

    def test_cache_ttl_expiry(self):
        cache = PerceptionCache(ttl_seconds=0.05)
        raw_image = MagicMock()
        sig = cache.compute_signature(raw_image)
        res = PerceptionResult(elements=[], sources_used=["test"])
        cache.set(sig, res)

        time.sleep(0.06)
        assert cache.get(sig) is None


# ==============================================================================
# 5. Foreground Application Detector Tests
# ==============================================================================

class TestForegroundApplicationDetector:
    def test_detector_context_extraction(self):
        detector = ForegroundApplicationDetector()
        context = detector.get_foreground_context()
        assert isinstance(context, ApplicationContext)
        assert isinstance(context.is_browser, bool)
        assert isinstance(context.app_name, str)

    def test_application_context_matching(self):
        ctx = ApplicationContext(app_name="Google Chrome", window_title="Google Search - Google Chrome")
        assert ctx.matches("chrome") is True
        assert ctx.matches("google") is True
        assert ctx.matches("notepad") is False
        assert ctx.is_browser is True


# ==============================================================================
# 6. Multi-Source PerceptionManager Tests
# ==============================================================================

class TestPerceptionManagerMultiSource:
    def test_fusion_prioritizes_accessibility_over_ocr(self):
        mock_acc_elem = UIElement(
            element_id="acc_btn",
            text="Submit Form",
            element_type="button",
            x=100,
            y=100,
            width=120,
            height=40,
            confidence=0.95,
            source="accessibility",
        )
        mock_acc = MockAccessibilityProvider(elements=[mock_acc_elem])

        mock_ocr_elem = MagicMock()
        mock_ocr_elem.text = "Submit Form"
        mock_ocr_elem.x = 102
        mock_ocr_elem.y = 101
        mock_ocr_elem.width = 118
        mock_ocr_elem.height = 39
        mock_ocr_elem.confidence = 0.8

        mock_ocr = MagicMock()
        mock_ocr.detect_text.return_value = [mock_ocr_elem]

        manager = PerceptionManager(
            ocr=mock_ocr,
            accessibility_provider=mock_acc,
            cache=PerceptionCache(ttl_seconds=0),
        )

        dummy_img = MagicMock()
        result = manager.analyze(image=dummy_img)
        assert len(result.elements) == 1
        winner = result.elements[0]
        assert winner.source == "FUSED"
        assert winner.text == "Submit Form"
        assert "ACCESSIBILITY" in result.sources_used
        assert "OCR" in result.sources_used
        assert result.ui_graph is not None

    def test_fallback_to_ocr_when_accessibility_empty(self):
        mock_acc = MockAccessibilityProvider(elements=[])
        
        mock_ocr_elem = MagicMock()
        mock_ocr_elem.text = "Start Here"
        mock_ocr_elem.x = 200
        mock_ocr_elem.y = 300
        mock_ocr_elem.width = 100
        mock_ocr_elem.height = 30
        mock_ocr_elem.confidence = 0.9

        mock_ocr = MagicMock()
        mock_ocr.detect_text.return_value = [mock_ocr_elem]

        manager = PerceptionManager(
            ocr=mock_ocr,
            accessibility_provider=mock_acc,
            cache=PerceptionCache(ttl_seconds=0),
        )

        dummy_img = MagicMock()
        result = manager.analyze(image=dummy_img)
        assert len(result.elements) == 1
        assert result.elements[0].source == "OCR"
        assert result.elements[0].text == "Start Here"


# ==============================================================================
# 7. SpatialReasoner Tests
# ==============================================================================

class TestSpatialReasonerPhase2:
    def setup_method(self):
        self.reasoner = SpatialReasoner()

    def test_resolve_axis_ordinal_horizontal_and_reverse(self):
        # 3 buttons in a row: B1(100, 50), B2(200, 50), B3(300, 50)
        b1 = UIElement(element_id="b1", text="First", element_type="button", x=80, y=30, width=40, height=40)
        b2 = UIElement(element_id="b2", text="Second", element_type="button", x=180, y=30, width=40, height=40)
        b3 = UIElement(element_id="b3", text="Third", element_type="button", x=280, y=30, width=40, height=40)
        elements = [b2, b3, b1]  # out of order

        # 2nd from left
        res = self.reasoner.resolve_axis_ordinal(elements, ordinal=2, axis="horizontal", direction="left_to_right")
        assert res.found is True
        assert res.element.element_id == "b2"

        # 1st from right (last from left)
        res_r = self.reasoner.resolve_axis_ordinal(elements, ordinal=1, axis="horizontal", direction="right_to_left")
        assert res_r.found is True
        assert res_r.element.element_id == "b3"

    def test_resolve_between(self):
        left_box = UIElement(element_id="left", text="Left Anchor", element_type="label", x=80, y=180, width=40, height=40)
        middle_box = UIElement(element_id="mid", text="Target Item", element_type="button", x=230, y=180, width=40, height=40)
        right_box = UIElement(element_id="right", text="Right Anchor", element_type="label", x=380, y=180, width=40, height=40)
        other_box = UIElement(element_id="other", text="Far Away", element_type="button", x=230, y=580, width=40, height=40)

        res = self.reasoner.resolve_between([middle_box, other_box], left_box, right_box)
        assert res.found is True
        assert res.element.element_id == "mid"

    def test_resolve_inside(self):
        container = UIElement(element_id="modal", text="Dialog Box", element_type="container", x=300, y=300, width=400, height=400)
        inside_btn = UIElement(element_id="ok_btn", text="OK", element_type="button", x=430, y=430, width=40, height=40)
        outside_btn = UIElement(element_id="out_btn", text="Close", element_type="button", x=80, y=80, width=40, height=40)

        res = self.reasoner.resolve_inside([inside_btn, outside_btn], container)
        assert res.found is True
        assert res.element.element_id == "ok_btn"

    def test_resolve_relational_router(self):
        ref = UIElement(element_id="ref", text="Email Label", element_type="label", x=180, y=180, width=40, height=40)
        inp = UIElement(element_id="inp", text="Input Field", element_type="input", x=180, y=250, width=40, height=40)
        res = self.reasoner.resolve_relational([inp], "below", ref)
        assert res.found is True
        assert res.element.element_id == "inp"


# ==============================================================================
# 8. TargetQuery Parsing Tests
# ==============================================================================

class TestTargetQueryParsing:
    def test_parse_ordinal_with_axis(self):
        q = parse_target_query("second button from the left")
        assert q.ordinal == 2
        assert q.ordinal_axis == "horizontal"
        assert q.ordinal_direction == "left_to_right"
        assert q.element_type == "button"

    def test_parse_relational_between(self):
        q = parse_target_query("input between Username and Cancel")
        assert q.relation == "between"
        assert q.reference == "username"
        assert q.metadata.get("reference_b") == "cancel"
        assert q.element_type == "input"

    def test_parse_relational_inside(self):
        q = parse_target_query("button inside settings dialog")
        assert q.relation == "inside"
        assert q.reference == "settings dialog"
        assert q.element_type == "button"


# ==============================================================================
# 9. TargetRanker Ambiguity & Disambiguation Tests
# ==============================================================================

class TestTargetRankerPhase2:
    def setup_method(self):
        self.ranker = TargetRanker()

    def test_unambiguous_ranking(self):
        btn1 = UIElement(element_id="b1", text="Submit Order", element_type="button", confidence=0.95, x=100, y=100, width=80, height=30)
        btn2 = UIElement(element_id="b2", text="Cancel Order", element_type="button", confidence=0.90, x=200, y=100, width=80, height=30)

        query = TargetQuery(text="Submit Order", element_type="button")
        ranking = self.ranker.rank([btn1, btn2], query)
        assert len(ranking.candidates) == 2
        assert ranking.best is not None
        assert ranking.best.element.element_id == "b1"
        assert ranking.is_ambiguous is False

    def test_ambiguity_detection_and_clarification_question(self):
        # Two identical "Edit" buttons on screen
        btn1 = UIElement(element_id="b1", text="Edit", element_type="button", x=100, y=100, width=60, height=25)
        btn2 = UIElement(element_id="b2", text="Edit", element_type="button", x=100, y=700, width=60, height=25)

        query = TargetQuery(text="Edit", element_type="button")
        ambiguity: AmbiguityResult = self.ranker.check_ambiguity([btn1, btn2], query)

        assert ambiguity.is_ambiguous is True
        assert len(ambiguity.candidates) == 2
        assert "multiple" in ambiguity.clarification_question.lower() or "which" in ambiguity.clarification_question.lower()


# ==============================================================================
# 10. ScrollPerceptionHandler Tests
# ==============================================================================

class TestScrollPerceptionHandler:
    def test_finds_target_immediately(self):
        elem = UIElement(element_id="e1", text="Accept Terms", element_type="button", confidence=0.95, x=450, y=380, width=100, height=40)
        observe_fn = MagicMock(return_value=ScreenObservation(elements=[elem]))
        scroll_fn = MagicMock()

        handler = ScrollPerceptionHandler(max_scroll_attempts=3)
        found, scrolls, reason = handler.find_target_with_scrolling(
            observe_fn=observe_fn,
            scroll_fn=scroll_fn,
            query=TargetQuery(text="Accept Terms", element_type="button"),
        )

        assert found is not None
        assert found.element_id == "e1"
        assert scrolls == 0
        scroll_fn.assert_not_called()

    def test_finds_target_after_scrolling(self):
        elem_found = UIElement(element_id="target_footer", text="Copyright", element_type="label", confidence=0.95, x=450, y=780, width=100, height=40)
        
        obs_empty = ScreenObservation(elements=[UIElement(element_id="hdr", text="Header", element_type="label", x=450, y=50, width=100, height=20)])
        obs_with_target = ScreenObservation(elements=[elem_found])

        observe_fn = MagicMock(side_effect=[obs_empty, obs_empty, obs_with_target])
        scroll_fn = MagicMock()

        handler = ScrollPerceptionHandler(max_scroll_attempts=4)
        found, scrolls, reason = handler.find_target_with_scrolling(
            observe_fn=observe_fn,
            scroll_fn=scroll_fn,
            query=TargetQuery(text="Copyright", element_type="label"),
        )

        assert found is not None
        assert found.element_id == "target_footer"
        assert scrolls == 2
        assert scroll_fn.call_count == 2

    def test_stops_at_max_scrolls(self):
        obs_empty = ScreenObservation(elements=[UIElement(element_id="body", text="Text", element_type="label", x=100, y=100, width=50, height=20)])
        observe_fn = MagicMock(return_value=obs_empty)
        scroll_fn = MagicMock()

        handler = ScrollPerceptionHandler(max_scroll_attempts=2)
        found, scrolls, reason = handler.find_target_with_scrolling(
            observe_fn=observe_fn,
            scroll_fn=scroll_fn,
            query=TargetQuery(text="Missing Link"),
            max_attempts=2,
        )

        assert found is None
        assert scrolls == 2
        assert "limit" in reason.lower() or "attempt" in reason.lower() or "exhausted" in reason.lower() or "not found" in reason.lower()


# ==============================================================================
# 11. Observation Diff Phase 2 Features
# ==============================================================================

class TestObservationDiffPhase2:
    def test_diff_detects_url_and_foreground_changes(self):
        obs_before = ScreenObservation(
            elements=[UIElement(element_id="1", text="Old", element_type="label", x=50, y=50, width=20, height=20)],
            url="https://site.com/step1",
            foreground_context=ApplicationContext(app_name="Chrome", window_title="Step 1"),
        )
        obs_after = ScreenObservation(
            elements=[UIElement(element_id="2", text="New", element_type="label", x=50, y=50, width=20, height=20)],
            url="https://site.com/step2",
            foreground_context=ApplicationContext(app_name="VSCode", window_title="app.py"),
        )

        diff = diff_observations(obs_before, obs_after)
        assert diff.url_changed is True
        assert diff.foreground_app_changed is True
        assert diff.has_meaningful_change is True
