"""Tests for SpatialReasoner — geometry-based spatial and ordinal reasoning."""

import pytest

from app.perception.spatial_reasoner import SpatialReasoner, _reading_order
from app.perception.ui_element import UIElement


def make_element(
    eid: str,
    text: str,
    x: int,
    y: int,
    width: int = 100,
    height: int = 30,
    element_type: str = "button",
) -> UIElement:
    return UIElement(
        element_id=eid,
        element_type=element_type,
        text=text,
        x=x,
        y=y,
        width=width,
        height=height,
    )


# ---------------------------------------------------------------------------
# Reading order
# ---------------------------------------------------------------------------


class TestReadingOrder:

    def test_vertical_list(self):
        """Top-to-bottom vertical list → ordinal = top-first."""
        notepad = make_element("1", "Notepad", x=100, y=100)
        calculator = make_element("2", "Calculator", x=100, y=160)
        paint = make_element("3", "Paint", x=100, y=220)
        word = make_element("4", "Word", x=100, y=280)

        ordered = _reading_order([word, paint, notepad, calculator])

        assert [e.text for e in ordered] == [
            "Notepad", "Calculator", "Paint", "Word"
        ]

    def test_horizontal_list(self):
        """Left-to-right horizontal list → ordinal = left-first."""
        search = make_element("1", "Search", x=100, y=50)
        images = make_element("2", "Images", x=250, y=50)
        videos = make_element("3", "Videos", x=400, y=50)

        ordered = _reading_order([videos, search, images])

        assert [e.text for e in ordered] == ["Search", "Images", "Videos"]

    def test_mixed_grid(self):
        """Two rows — top row first, then bottom row, each left-to-right."""
        a = make_element("a", "A", x=0, y=0)
        b = make_element("b", "B", x=100, y=0)
        c = make_element("c", "C", x=0, y=50)
        d = make_element("d", "D", x=100, y=50)

        ordered = _reading_order([d, b, c, a])

        assert [e.text for e in ordered] == ["A", "B", "C", "D"]


# ---------------------------------------------------------------------------
# Ordinal resolution
# ---------------------------------------------------------------------------


class TestOrdinalResolution:

    def setup_method(self):
        self.reasoner = SpatialReasoner()
        self.elements = [
            make_element("1", "Notepad", x=100, y=100),
            make_element("2", "Calculator", x=100, y=160),
            make_element("3", "Paint", x=100, y=220),
            make_element("4", "Word", x=100, y=280),
        ]

    def test_first(self):
        result = self.reasoner.resolve_ordinal(self.elements, 1)
        assert result.found
        assert result.element.text == "Notepad"

    def test_second(self):
        result = self.reasoner.resolve_ordinal(self.elements, 2)
        assert result.found
        assert result.element.text == "Calculator"

    def test_third(self):
        result = self.reasoner.resolve_ordinal(self.elements, 3)
        assert result.found
        assert result.element.text == "Paint"

    def test_last(self):
        result = self.reasoner.resolve_ordinal(self.elements, -1)
        assert result.found
        assert result.element.text == "Word"

    def test_second_last(self):
        result = self.reasoner.resolve_ordinal(self.elements, -2)
        assert result.found
        assert result.element.text == "Paint"

    def test_out_of_range_positive(self):
        result = self.reasoner.resolve_ordinal(self.elements, 10)
        assert not result.found

    def test_out_of_range_negative(self):
        result = self.reasoner.resolve_ordinal(self.elements, -10)
        assert not result.found

    def test_empty_list(self):
        result = self.reasoner.resolve_ordinal([], 1)
        assert not result.found

    def test_single_element_first(self):
        result = self.reasoner.resolve_ordinal(
            [self.elements[0]], 1
        )
        assert result.found
        assert result.element.text == "Notepad"

    def test_single_element_last(self):
        result = self.reasoner.resolve_ordinal(
            [self.elements[0]], -1
        )
        assert result.found
        assert result.element.text == "Notepad"


# ---------------------------------------------------------------------------
# Directional resolution
# ---------------------------------------------------------------------------


class TestDirectionalResolution:

    def setup_method(self):
        self.reasoner = SpatialReasoner()

    def _make_grid(self):
        """
        Layout:
            TopLeft(0,0)    TopRight(200,0)
            BotLeft(0,150)  BotRight(200,150)
            Calculator(100,75) — center
        """
        return {
            "calc": make_element("c", "Calculator", x=75, y=50, width=100, height=30),
            "above": make_element("a", "Above", x=75, y=0, width=100, height=30),
            "below": make_element("b", "Below", x=75, y=110, width=100, height=30),
            "left": make_element("l", "Left", x=0, y=50, width=60, height=30),
            "right": make_element("r", "Right", x=200, y=50, width=100, height=30),
        }

    def test_above(self):
        grid = self._make_grid()
        candidates = [grid["above"], grid["below"], grid["left"], grid["right"]]
        result = self.reasoner.resolve_directional(
            candidates, "above", grid["calc"]
        )
        assert result.found
        assert result.element.text == "Above"

    def test_below(self):
        grid = self._make_grid()
        candidates = [grid["above"], grid["below"], grid["left"], grid["right"]]
        result = self.reasoner.resolve_directional(
            candidates, "below", grid["calc"]
        )
        assert result.found
        assert result.element.text == "Below"

    def test_left(self):
        grid = self._make_grid()
        candidates = [grid["above"], grid["below"], grid["left"], grid["right"]]
        result = self.reasoner.resolve_directional(
            candidates, "left", grid["calc"]
        )
        assert result.found
        assert result.element.text == "Left"

    def test_right(self):
        grid = self._make_grid()
        candidates = [grid["above"], grid["below"], grid["left"], grid["right"]]
        result = self.reasoner.resolve_directional(
            candidates, "right", grid["calc"]
        )
        assert result.found
        assert result.element.text == "Right"

    def test_no_element_in_direction(self):
        calc = make_element("c", "Calculator", x=100, y=100)
        # Only elements below
        below = make_element("b", "Below", x=100, y=200)
        result = self.reasoner.resolve_directional(
            [below], "above", calc
        )
        assert not result.found

    def test_unknown_relation(self):
        calc = make_element("c", "Calculator", x=100, y=100)
        result = self.reasoner.resolve_directional(
            [], "diagonal", calc
        )
        assert not result.found


# ---------------------------------------------------------------------------
# Proximity resolution
# ---------------------------------------------------------------------------


class TestProximityResolution:

    def setup_method(self):
        self.reasoner = SpatialReasoner()

    def test_nearest(self):
        reference = make_element("ref", "Search", x=200, y=100)
        close = make_element("1", "Images", x=210, y=100)
        far = make_element("2", "Videos", x=500, y=100)

        result = self.reasoner.resolve_nearest(
            [close, far], reference
        )

        assert result.found
        assert result.element.text == "Images"

    def test_no_element_within_threshold(self):
        reference = make_element("ref", "Search", x=100, y=100)
        far = make_element("1", "Far", x=2000, y=2000)

        result = self.reasoner.resolve_nearest(
            [far], reference
        )

        assert not result.found

    def test_empty_candidates(self):
        reference = make_element("ref", "Search", x=100, y=100)
        result = self.reasoner.resolve_nearest([], reference)
        assert not result.found


# ---------------------------------------------------------------------------
# Ordered candidates
# ---------------------------------------------------------------------------


class TestOrderedCandidates:

    def test_returns_reading_order(self):
        reasoner = SpatialReasoner()
        a = make_element("1", "A", x=100, y=100)
        b = make_element("2", "B", x=100, y=150)
        c = make_element("3", "C", x=100, y=200)

        result = reasoner.ordered_candidates([c, a, b])

        assert [e.text for e in result] == ["A", "B", "C"]
