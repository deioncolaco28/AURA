"""
app/perception/spatial_reasoner.py

Geometry-based spatial and structural reasoning over UI elements.

The SpatialReasoner resolves TargetQuery objects against a list of
UIElement objects using actual detected coordinates.

It supports:
    Ordinal     : first / second / third / nth / last / second-last
    Directional : above / below / left / right
    Proximity   : nearest / closest / beside / next to
    Group-aware : ordered within a candidate group

No application-specific hard-coding.
No fixed coordinate assumptions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from app.perception.ui_element import UIElement


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class SpatialResult:
    """The outcome of a spatial reasoning query."""

    found: bool
    element: UIElement | None = None
    score: float = 0.0
    reason: str = ""
    candidates_considered: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Row/column detection helpers
# ---------------------------------------------------------------------------


def _group_by_rows(
    elements: list[UIElement],
    row_tolerance: int = 20,
) -> list[list[UIElement]]:
    """
    Group elements into rows based on vertical proximity.

    Elements whose vertical centers differ by less than `row_tolerance`
    pixels are placed in the same row.

    Rows are returned sorted top-to-bottom.
    Each row is sorted left-to-right.
    """

    if not elements:
        return []

    sorted_by_y = sorted(
        elements,
        key=lambda e: e.center[1],
    )

    rows: list[list[UIElement]] = []
    current_row: list[UIElement] = [sorted_by_y[0]]
    current_y = sorted_by_y[0].center[1]

    for element in sorted_by_y[1:]:
        cy = element.center[1]

        if abs(cy - current_y) <= row_tolerance:
            current_row.append(element)
        else:
            # Sort the completed row left-to-right and save it.
            current_row.sort(key=lambda e: e.center[0])
            rows.append(current_row)

            current_row = [element]
            current_y = cy

    # Save the last row.
    current_row.sort(key=lambda e: e.center[0])
    rows.append(current_row)

    return rows


def _reading_order(elements: list[UIElement]) -> list[UIElement]:
    """
    Return elements in reading order (top-to-bottom, left-to-right).

    This gives an intuitive 'first/second/third' ordinal ordering
    for most UI layouts (menus, lists, search results, etc.).
    """

    rows = _group_by_rows(elements)

    ordered: list[UIElement] = []

    for row in rows:
        ordered.extend(row)

    return ordered


def _distance(a: UIElement, b: UIElement) -> float:
    """Euclidean distance between element centers."""

    ax, ay = a.center
    bx, by = b.center

    return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2)


# ---------------------------------------------------------------------------
# SpatialReasoner
# ---------------------------------------------------------------------------


class SpatialReasoner:
    """
    Resolves spatial/structural target queries against UI elements.

    All reasoning uses actual detected geometry.
    No coordinates are hard-coded.
    No application names are hard-coded.
    """

    # Thresholds -------------------------------------------------------

    # Maximum pixel distance for "directly above/below/left/right".
    DIRECT_ALIGNMENT_THRESHOLD = 60

    # Maximum pixel distance for "nearest / beside / next to".
    PROXIMITY_THRESHOLD = 200

    # Row grouping tolerance (see _group_by_rows).
    ROW_TOLERANCE = 20

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def resolve_ordinal(
        self,
        elements: list[UIElement],
        ordinal: int,
    ) -> SpatialResult:
        """
        Select the nth element in reading order.

        Parameters
        ----------
        elements : list[UIElement]
            Candidate elements.
        ordinal : int
            1-based for positive values (1 = first).
            Negative values count from the end (-1 = last, -2 = second-last).

        Returns
        -------
        SpatialResult
        """

        if not elements:
            return SpatialResult(
                found=False,
                reason="No candidate elements provided.",
                candidates_considered=0,
            )

        ordered = _reading_order(elements)
        n = len(ordered)

        if ordinal > 0:
            index = ordinal - 1  # convert to 0-based
        else:
            # -1 → last (index n-1), -2 → second-last (index n-2), …
            index = n + ordinal

        if index < 0 or index >= n:
            return SpatialResult(
                found=False,
                reason=(
                    f"Ordinal {ordinal} is out of range "
                    f"for {n} candidates."
                ),
                candidates_considered=n,
            )

        selected = ordered[index]

        ordinal_label = _ordinal_label(ordinal, n)

        return SpatialResult(
            found=True,
            element=selected,
            score=1.0,
            reason=f"Selected {ordinal_label} element in reading order.",
            candidates_considered=n,
            metadata={
                "ordinal": ordinal,
                "index": index,
                "reading_order": [e.element_id for e in ordered],
            },
        )

    def resolve_directional(
        self,
        elements: list[UIElement],
        relation: str,
        reference_element: UIElement,
    ) -> SpatialResult:
        """
        Find the element that is above/below/left/right of a reference.

        Parameters
        ----------
        elements : list[UIElement]
            Candidate elements (should not include the reference itself).
        relation : str
            One of: "above", "below", "left", "right".
        reference_element : UIElement
            The reference anchor element.

        Returns
        -------
        SpatialResult
        """

        relation = relation.strip().lower()

        if relation not in ("above", "below", "left", "right"):
            return SpatialResult(
                found=False,
                reason=f"Unknown directional relation: '{relation}'.",
                candidates_considered=len(elements),
            )

        if not elements:
            return SpatialResult(
                found=False,
                reason="No candidate elements provided.",
                candidates_considered=0,
            )

        rx, ry = reference_element.center

        scored: list[tuple[float, UIElement, str]] = []

        for element in elements:
            cx, cy = element.center

            score, passes = self._directional_score(
                cx, cy, rx, ry, relation
            )

            if passes:
                scored.append((score, element, relation))

        if not scored:
            return SpatialResult(
                found=False,
                reason=(
                    f"No element found {relation} of "
                    f"'{reference_element.text or reference_element.element_id}'."
                ),
                candidates_considered=len(elements),
            )

        # Choose the highest-scoring (closest qualifying) element.
        scored.sort(key=lambda t: t[0], reverse=True)

        best_score, best_element, _ = scored[0]

        return SpatialResult(
            found=True,
            element=best_element,
            score=best_score,
            reason=(
                f"Element is {relation} of "
                f"'{reference_element.text or reference_element.element_id}'."
            ),
            candidates_considered=len(elements),
        )

    def resolve_nearest(
        self,
        elements: list[UIElement],
        reference_element: UIElement,
    ) -> SpatialResult:
        """
        Find the element closest to the reference element.

        Parameters
        ----------
        elements : list[UIElement]
            Candidate elements (should not include the reference itself).
        reference_element : UIElement
            The reference anchor.

        Returns
        -------
        SpatialResult
        """

        if not elements:
            return SpatialResult(
                found=False,
                reason="No candidate elements provided.",
                candidates_considered=0,
            )

        scored = sorted(
            elements,
            key=lambda e: _distance(e, reference_element),
        )

        nearest = scored[0]
        dist = _distance(nearest, reference_element)

        if dist > self.PROXIMITY_THRESHOLD:
            return SpatialResult(
                found=False,
                reason=(
                    f"Nearest element is {dist:.0f}px away "
                    f"(threshold {self.PROXIMITY_THRESHOLD}px)."
                ),
                candidates_considered=len(elements),
            )

        # Score: 1.0 for distance=0, approaching 0 at PROXIMITY_THRESHOLD.
        score = max(
            0.0,
            1.0 - dist / self.PROXIMITY_THRESHOLD,
        )

        return SpatialResult(
            found=True,
            element=nearest,
            score=score,
            reason=f"Nearest element ({dist:.0f}px away).",
            candidates_considered=len(elements),
            metadata={"distance_px": dist},
        )

    def ordered_candidates(
        self,
        elements: list[UIElement],
    ) -> list[UIElement]:
        """
        Return elements sorted in reading order (top-to-bottom, left-to-right).

        Useful for callers that need the full ordered list rather than
        a single resolved element.
        """

        return _reading_order(elements)

    # ------------------------------------------------------------------
    # Internal scoring
    # ------------------------------------------------------------------

    def _directional_score(
        self,
        cx: int,
        cy: int,
        rx: int,
        ry: int,
        relation: str,
    ) -> tuple[float, bool]:
        """
        Compute a directional quality score for a candidate.

        Returns (score, qualifies).

        The score is higher for elements that are clearly in the
        specified direction and closely aligned with the reference.
        """

        dx = cx - rx  # positive → candidate is to the right
        dy = cy - ry  # positive → candidate is below

        if relation == "above":
            if dy >= 0:
                return 0.0, False  # not above
            # Score based on vertical dominance and closeness.
            vertical_dominance = (
                abs(dy) > abs(dx)
            )
            score = (
                1.0 / (1.0 + abs(dy))
                if vertical_dominance
                else 0.3 / (1.0 + abs(dy))
            )
            return score, True

        if relation == "below":
            if dy <= 0:
                return 0.0, False  # not below
            vertical_dominance = abs(dy) > abs(dx)
            score = (
                1.0 / (1.0 + abs(dy))
                if vertical_dominance
                else 0.3 / (1.0 + abs(dy))
            )
            return score, True

        if relation == "left":
            if dx >= 0:
                return 0.0, False  # not to the left
            horizontal_dominance = abs(dx) > abs(dy)
            score = (
                1.0 / (1.0 + abs(dx))
                if horizontal_dominance
                else 0.3 / (1.0 + abs(dx))
            )
            return score, True

        if relation == "right":
            if dx <= 0:
                return 0.0, False  # not to the right
            horizontal_dominance = abs(dx) > abs(dy)
            score = (
                1.0 / (1.0 + abs(dx))
                if horizontal_dominance
                else 0.3 / (1.0 + abs(dx))
            )
            return score, True

        return 0.0, False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ordinal_label(ordinal: int, total: int) -> str:
    """Return a human-readable ordinal label."""

    if ordinal == -1 or (ordinal > 0 and ordinal == total):
        return "last"
    if ordinal == -2 or (ordinal > 0 and ordinal == total - 1):
        return "second-last"
    if ordinal < 0:
        return f"{abs(ordinal)}-from-last"

    _words = {
        1: "first",
        2: "second",
        3: "third",
        4: "fourth",
        5: "fifth",
    }

    return _words.get(ordinal, f"{ordinal}th")
