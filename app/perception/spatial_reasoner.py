"""
app/perception/spatial_reasoner.py

Geometry-based spatial and structural reasoning over UI elements.

The SpatialReasoner resolves TargetQuery objects against a list of
UIElement objects using actual detected coordinates.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from app.perception.ui_element import UIElement


@dataclass
class SpatialResult:
    """The outcome of a spatial reasoning query."""

    found: bool
    element: UIElement | None = None
    score: float = 0.0
    reason: str = ""
    candidates_considered: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


def _group_by_rows(
    elements: list[UIElement],
    row_tolerance: int = 20,
) -> list[list[UIElement]]:
    """Group elements into rows based on vertical proximity."""
    if not elements:
        return []

    sorted_by_y = sorted(elements, key=lambda e: e.center[1])
    rows: list[list[UIElement]] = []
    current_row: list[UIElement] = [sorted_by_y[0]]
    current_y = sorted_by_y[0].center[1]

    for element in sorted_by_y[1:]:
        cy = element.center[1]
        if abs(cy - current_y) <= row_tolerance:
            current_row.append(element)
        else:
            current_row.sort(key=lambda e: e.center[0])
            rows.append(current_row)
            current_row = [element]
            current_y = cy

    current_row.sort(key=lambda e: e.center[0])
    rows.append(current_row)
    return rows


def _group_by_columns(
    elements: list[UIElement],
    col_tolerance: int = 20,
) -> list[list[UIElement]]:
    """Group elements into columns based on horizontal proximity."""
    if not elements:
        return []

    sorted_by_x = sorted(elements, key=lambda e: e.center[0])
    cols: list[list[UIElement]] = []
    current_col: list[UIElement] = [sorted_by_x[0]]
    current_x = sorted_by_x[0].center[0]

    for element in sorted_by_x[1:]:
        cx = element.center[0]
        if abs(cx - current_x) <= col_tolerance:
            current_col.append(element)
        else:
            current_col.sort(key=lambda e: e.center[1])
            cols.append(current_col)
            current_col = [element]
            current_x = cx

    current_col.sort(key=lambda e: e.center[1])
    cols.append(current_col)
    return cols


def _reading_order(elements: list[UIElement]) -> list[UIElement]:
    """Return elements in standard reading order (top-to-bottom, left-to-right)."""
    rows = _group_by_rows(elements)
    ordered: list[UIElement] = []
    for row in rows:
        ordered.extend(row)
    return ordered


def _distance(a: UIElement, b: UIElement) -> float:
    """Euclidean distance between element centers."""
    ax, ay = a.center
    bx, by = b.center
    return math.hypot(ax - bx, ay - by)


class SpatialReasoner:
    """
    Resolves spatial/structural target queries against UI elements.
    """

    DIRECT_ALIGNMENT_THRESHOLD = 60
    PROXIMITY_THRESHOLD = 300
    ROW_TOLERANCE = 20
    COL_TOLERANCE = 20

    def ordered_candidates(self, elements: list[UIElement]) -> list[UIElement]:
        """Return candidates sorted in reading order."""
        return _reading_order(elements)

    def resolve_ordinal(
        self,
        elements: list[UIElement],
        ordinal: int,
    ) -> SpatialResult:
        """Select the nth element in reading order."""
        return self.resolve_axis_ordinal(
            elements=elements,
            ordinal=ordinal,
            axis="reading_order",
            direction="left_to_right",
        )

    def resolve_axis_ordinal(
        self,
        elements: list[UIElement],
        ordinal: int,
        axis: str = "reading_order",
        direction: str = "left_to_right",
    ) -> SpatialResult:
        """
        Select the nth element sorted along an axis and direction.

        axis: 'reading_order', 'horizontal', 'vertical'
        direction: 'left_to_right', 'right_to_left', 'top_to_bottom', 'bottom_to_top'
        """
        if not elements:
            return SpatialResult(
                found=False,
                reason="No candidate elements provided.",
                candidates_considered=0,
            )

        if axis == "horizontal":
            ordered = sorted(elements, key=lambda e: e.center[0])
            if direction == "right_to_left":
                ordered.reverse()
        elif axis == "vertical":
            ordered = sorted(elements, key=lambda e: e.center[1])
            if direction == "bottom_to_top":
                ordered.reverse()
        else:
            ordered = _reading_order(elements)

        n = len(ordered)
        if ordinal > 0:
            index = ordinal - 1
        else:
            index = n + ordinal

        if index < 0 or index >= n:
            return SpatialResult(
                found=False,
                reason=f"Ordinal {ordinal} is out of range for {n} candidates.",
                candidates_considered=n,
            )

        selected = ordered[index]
        ordinal_label = _ordinal_label(ordinal, n)

        return SpatialResult(
            found=True,
            element=selected,
            score=1.0,
            reason=f"Selected {ordinal_label} element along {axis} ({direction}).",
            candidates_considered=n,
            metadata={
                "ordinal": ordinal,
                "index": index,
                "ordered_ids": [e.element_id for e in ordered],
            },
        )

    def resolve_directional(
        self,
        elements: list[UIElement],
        relation: str,
        reference_element: UIElement,
    ) -> SpatialResult:
        """Find the element that is above/below/left/right of a reference."""
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
            if element.element_id == reference_element.element_id:
                continue
            cx, cy = element.center
            score, passes = self._directional_score(cx, cy, rx, ry, relation)
            if passes:
                scored.append((score, element, relation))

        if not scored:
            return SpatialResult(
                found=False,
                reason=f"No element found {relation} of '{reference_element.text or reference_element.element_id}'.",
                candidates_considered=len(elements),
            )

        scored.sort(key=lambda t: t[0], reverse=True)
        best_score, best_element, _ = scored[0]

        return SpatialResult(
            found=True,
            element=best_element,
            score=best_score,
            reason=f"Element is {relation} of '{reference_element.text or reference_element.element_id}'.",
            candidates_considered=len(elements),
        )

    def resolve_nearest(
        self,
        elements: list[UIElement],
        reference_element: UIElement,
    ) -> SpatialResult:
        """Find the element closest to the reference element."""
        if not elements:
            return SpatialResult(
                found=False,
                reason="No candidate elements provided.",
                candidates_considered=0,
            )

        valid_candidates = [e for e in elements if e.element_id != reference_element.element_id]
        if not valid_candidates:
            return SpatialResult(
                found=False,
                reason="No valid candidate elements provided.",
                candidates_considered=0,
            )

        scored = sorted(
            valid_candidates,
            key=lambda e: _distance(e, reference_element),
        )

        nearest = scored[0]
        dist = _distance(nearest, reference_element)

        if dist > self.PROXIMITY_THRESHOLD:
            return SpatialResult(
                found=False,
                reason=f"Nearest element is {dist:.0f}px away (threshold {self.PROXIMITY_THRESHOLD}px).",
                candidates_considered=len(elements),
            )

        score = max(0.0, 1.0 - dist / self.PROXIMITY_THRESHOLD)

        return SpatialResult(
            found=True,
            element=nearest,
            score=score,
            reason=f"Nearest element ({dist:.0f}px away).",
            candidates_considered=len(elements),
            metadata={"distance_px": dist},
        )

    def resolve_beside(
        self,
        elements: list[UIElement],
        reference_element: UIElement,
    ) -> SpatialResult:
        """Find the element beside / next to the reference element."""
        if not elements:
            return SpatialResult(
                found=False,
                reason="No candidate elements provided.",
                candidates_considered=0,
            )

        rx, ry = reference_element.center
        scored = []
        for elem in elements:
            if elem.element_id == reference_element.element_id:
                continue
            cx, cy = elem.center
            dy = abs(cy - ry)
            dx = abs(cx - rx)
            if dy <= self.ROW_TOLERANCE * 2 and dx > 0:
                dist = _distance(elem, reference_element)
                if dist <= self.PROXIMITY_THRESHOLD:
                    score = max(0.0, 1.0 - dist / self.PROXIMITY_THRESHOLD)
                    scored.append((score, elem, dist))

        if not scored:
            return self.resolve_nearest(elements, reference_element)

        scored.sort(key=lambda t: t[0], reverse=True)
        best_score, best_elem, dist = scored[0]

        return SpatialResult(
            found=True,
            element=best_elem,
            score=best_score,
            reason=f"Element is beside '{reference_element.text or reference_element.element_id}' ({dist:.0f}px away).",
            candidates_considered=len(elements),
            metadata={"distance_px": dist},
        )

    def resolve_between(
        self,
        elements: list[UIElement],
        anchor_a: UIElement,
        anchor_b: UIElement,
    ) -> SpatialResult:
        """Find the element located between two reference elements."""
        if not elements:
            return SpatialResult(
                found=False,
                reason="No candidate elements provided.",
                candidates_considered=0,
            )

        ax, ay = anchor_a.center
        bx, by = anchor_b.center

        min_x, max_x = min(ax, bx), max(ax, bx)
        min_y, max_y = min(ay, by), max(ay, by)

        candidates = []
        for elem in elements:
            if elem.element_id in (anchor_a.element_id, anchor_b.element_id):
                continue
            ex, ey = elem.center
            # Check if within bounding box of both anchors
            if min_x - 10 <= ex <= max_x + 10 and min_y - 20 <= ey <= max_y + 20:
                # Calculate distance to line segment AB
                line_dist = abs((by - ay) * ex - (bx - ax) * ey + bx * ay - by * ax) / (math.hypot(by - ay, bx - ax) or 1)
                candidates.append((line_dist, elem))

        if not candidates:
            return SpatialResult(
                found=False,
                reason=f"No element found between '{anchor_a.text or anchor_a.element_id}' and '{anchor_b.text or anchor_b.element_id}'.",
                candidates_considered=len(elements),
            )

        candidates.sort(key=lambda item: item[0])
        best_elem = candidates[0][1]

        return SpatialResult(
            found=True,
            element=best_elem,
            score=0.9,
            reason=f"Element is between '{anchor_a.text or anchor_a.element_id}' and '{anchor_b.text or anchor_b.element_id}'.",
            candidates_considered=len(elements),
        )

    def resolve_inside(
        self,
        elements: list[UIElement],
        container: UIElement,
    ) -> SpatialResult:
        """Find elements geometrically inside container bounds."""
        inside_elems = [
            e for e in elements
            if e.element_id != container.element_id and container.contains_point(*e.center)
        ]
        if not inside_elems:
            return SpatialResult(
                found=False,
                reason=f"No element found inside '{container.text or container.element_id}'.",
                candidates_considered=len(elements),
            )

        return SpatialResult(
            found=True,
            element=inside_elems[0],
            score=0.95,
            reason=f"Element is inside '{container.text or container.element_id}'.",
            candidates_considered=len(elements),
            metadata={"inside_count": len(inside_elems)},
        )

    def resolve_relational(
        self,
        elements: list[UIElement],
        relation: str,
        reference_element: UIElement,
        metadata: dict[str, Any] | None = None,
    ) -> SpatialResult:
        """Resolve any spatial relation."""
        rel = relation.strip().lower()
        if rel in ("above", "below", "left", "right"):
            return self.resolve_directional(elements, rel, reference_element)
        if rel in ("beside", "next to"):
            return self.resolve_beside(elements, reference_element)
        if rel in ("nearest", "closest", "near"):
            return self.resolve_nearest(elements, reference_element)
        if rel in ("inside", "in", "contains"):
            return self.resolve_inside(elements, reference_element)
        if rel == "between" and metadata and "reference_b_element" in metadata:
            return self.resolve_between(elements, reference_element, metadata["reference_b_element"])

        return SpatialResult(
            found=False,
            reason=f"Unknown spatial relation: '{relation}'.",
            candidates_considered=len(elements),
        )

    def _directional_score(
        self,
        cx: int,
        cy: int,
        rx: int,
        ry: int,
        relation: str,
    ) -> tuple[float, bool]:
        dx = cx - rx
        dy = cy - ry

        if relation == "above":
            if dy >= 0:
                return 0.0, False
            vertical_dominance = abs(dy) > abs(dx)
            score = 1.0 / (1.0 + abs(dy)) if vertical_dominance else 0.3 / (1.0 + abs(dy))
            return score, True

        if relation == "below":
            if dy <= 0:
                return 0.0, False
            vertical_dominance = abs(dy) > abs(dx)
            score = 1.0 / (1.0 + abs(dy)) if vertical_dominance else 0.3 / (1.0 + abs(dy))
            return score, True

        if relation == "left":
            if dx >= 0:
                return 0.0, False
            horizontal_dominance = abs(dx) > abs(dy)
            score = 1.0 / (1.0 + abs(dx)) if horizontal_dominance else 0.3 / (1.0 + abs(dx))
            return score, True

        if relation == "right":
            if dx <= 0:
                return 0.0, False
            horizontal_dominance = abs(dx) > abs(dy)
            score = 1.0 / (1.0 + abs(dx)) if horizontal_dominance else 0.3 / (1.0 + abs(dx))
            return score, True

        return 0.0, False


def _ordinal_label(ordinal: int, total: int) -> str:
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
