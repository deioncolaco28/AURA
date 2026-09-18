"""
app/perception/target_query.py

Structured representation of a user's target request.

A TargetQuery captures the intent behind a target reference so
that the spatial reasoner and target ranker can resolve it against
actual perceived UI elements without application-specific hard-coding.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Ordinal constants
# ---------------------------------------------------------------------------

ORDINAL_FIRST = 1
ORDINAL_LAST = -1         # last element
ORDINAL_SECOND_LAST = -2  # second from last

# ---------------------------------------------------------------------------
# Relation constants
# ---------------------------------------------------------------------------

RELATION_ABOVE = "above"
RELATION_BELOW = "below"
RELATION_LEFT = "left"
RELATION_RIGHT = "right"
RELATION_NEAREST = "nearest"
RELATION_BESIDE = "beside"
RELATION_BETWEEN = "between"
RELATION_INSIDE = "inside"
RELATION_CONTAINS = "contains"


# ---------------------------------------------------------------------------
# TargetQuery
# ---------------------------------------------------------------------------


@dataclass
class TargetQuery:
    """
    Structured query representing what UI element the user means.
    """

    text: str | None = None
    element_type: str | None = None
    description: str | None = None
    ordinal: int | None = None
    ordinal_axis: str | None = None          # "horizontal", "vertical", "reading_order"
    ordinal_direction: str | None = None     # "left_to_right", "right_to_left", "top_to_bottom", "bottom_to_top"
    relation: str | None = None
    reference: str | None = None
    group: str | None = None
    region: str | None = None
    application_context: str | None = None
    minimum_confidence: float = 0.50
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def has_ordinal(self) -> bool:
        """True when an ordinal specifier is present."""
        return self.ordinal is not None

    @property
    def has_relation(self) -> bool:
        """True when a spatial relation to a reference is specified."""
        return (
            self.relation is not None
            and self.reference is not None
        )

    @property
    def is_simple_text(self) -> bool:
        """
        True when the query is a plain text label with no
        ordinal, relational, or group constraint.
        """
        return (
            self.text is not None
            and self.ordinal is None
            and self.relation is None
            and self.group is None
        )

    @property
    def is_reverse_ordinal(self) -> bool:
        """True when the ordinal counts from the end (negative)."""
        return (
            self.ordinal is not None
            and self.ordinal < 0
        )

    def describe(self) -> str:
        """Return a human-readable description of the query."""
        parts: list[str] = []

        if self.ordinal is not None:
            if self.ordinal == ORDINAL_LAST:
                parts.append("last")
            elif self.ordinal == ORDINAL_SECOND_LAST:
                parts.append("second-last")
            elif self.ordinal > 0:
                ordinal_words = {
                    1: "first",
                    2: "second",
                    3: "third",
                    4: "fourth",
                    5: "fifth",
                }
                parts.append(
                    ordinal_words.get(
                        self.ordinal,
                        f"{self.ordinal}th",
                    )
                )
            if self.ordinal_direction == "left_to_right":
                parts.append("from the left")
            elif self.ordinal_direction == "top_to_bottom":
                parts.append("from the top")

        if self.element_type:
            parts.append(self.element_type)

        if self.group:
            parts.append(self.group)

        if self.text:
            parts.append(f'"{self.text}"')

        if self.relation and self.reference:
            parts.append(f"{self.relation} {self.reference}")

        if self.region:
            parts.append(f"in {self.region}")

        if not parts:
            return "unspecified target"

        return " ".join(parts)


def parse_ordinal(text: str) -> int | None:
    """Parse a natural-language ordinal string into an integer."""
    text = text.strip().lower()

    _word_map: dict[str, int] = {
        "first": 1,
        "second": 2,
        "third": 3,
        "fourth": 4,
        "fifth": 5,
        "sixth": 6,
        "seventh": 7,
        "eighth": 8,
        "ninth": 9,
        "tenth": 10,
        "last": ORDINAL_LAST,
        "second-last": ORDINAL_SECOND_LAST,
        "second last": ORDINAL_SECOND_LAST,
        "third-last": -3,
        "third last": -3,
    }

    if text in _word_map:
        return _word_map[text]

    for suffix in ("st", "nd", "rd", "th"):
        if text.endswith(suffix):
            numeric_part = text[: -len(suffix)]
            try:
                return int(numeric_part)
            except ValueError:
                pass

    try:
        return int(text)
    except ValueError:
        return None


def parse_target_query(phrase: str) -> TargetQuery:
    """
    Parse a natural language target phrase or instruction into a structured TargetQuery.
    """
    if not phrase or not phrase.strip():
        return TargetQuery()

    cleaned = phrase.strip()

    prefixes_to_strip = [
        "click on the ", "click the ", "click ",
        "select the ", "select ",
        "choose the ", "choose ",
        "press the ", "press ",
        "tap the ", "tap ",
        "open the ", "open ",
        "the ",
    ]
    cleaned_lower = cleaned.lower()
    for prefix in prefixes_to_strip:
        if cleaned_lower.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
            cleaned_lower = cleaned.lower()
            break

    # 1. Check for directional ordinals: e.g. "second button from the left", "first item from top"
    for dir_pattern, axis, direction in [
        (" from the left", "horizontal", "left_to_right"),
        (" from left", "horizontal", "left_to_right"),
        (" from the right", "horizontal", "right_to_left"),
        (" from right", "horizontal", "right_to_left"),
        (" from the top", "vertical", "top_to_bottom"),
        (" from top", "vertical", "top_to_bottom"),
        (" from the bottom", "vertical", "bottom_to_top"),
        (" from bottom", "vertical", "bottom_to_top"),
    ]:
        if dir_pattern in cleaned_lower:
            prefix_part = cleaned_lower.split(dir_pattern)[0].strip()
            words = prefix_part.split()
            if words:
                ord_val = parse_ordinal(words[0])
                if ord_val is not None:
                    elem_type = " ".join(words[1:]).strip() if len(words) > 1 else None
                    return TargetQuery(
                        element_type=elem_type or "button",
                        ordinal=ord_val,
                        ordinal_axis=axis,
                        ordinal_direction=direction,
                    )

    # 2. Check for "between X and Y"
    if " between " in cleaned_lower and " and " in cleaned_lower:
        prefix_part, rest = cleaned_lower.split(" between ", 1)
        if " and " in rest:
            ref_a, ref_b = rest.split(" and ", 1)
            elem_type = prefix_part.strip() or None
            return TargetQuery(
                element_type=elem_type,
                relation=RELATION_BETWEEN,
                reference=ref_a.strip().strip("\"'.,"),
                metadata={"reference_b": ref_b.strip().strip("\"'.,")},
            )

    # 3. Check for other spatial relationships (relational queries)
    relational_markers = [
        (" to the right of ", RELATION_RIGHT),
        (" to the left of ", RELATION_LEFT),
        (" to the right ", RELATION_RIGHT),
        (" to the left ", RELATION_LEFT),
        (" right of ", RELATION_RIGHT),
        (" left of ", RELATION_LEFT),
        (" below ", RELATION_BELOW),
        (" under ", RELATION_BELOW),
        (" above ", RELATION_ABOVE),
        (" next to ", RELATION_BESIDE),
        (" beside ", RELATION_BESIDE),
        (" inside ", RELATION_INSIDE),
        (" contains ", RELATION_CONTAINS),
        (" near ", RELATION_NEAREST),
        (" nearest ", RELATION_NEAREST),
        (" closest to ", RELATION_NEAREST),
    ]

    for marker, relation in relational_markers:
        if marker in cleaned_lower:
            parts = cleaned_lower.split(marker, 1)
            target_type = parts[0].strip()
            ref_idx = cleaned_lower.find(marker) + len(marker)
            reference = cleaned[ref_idx:].strip().strip("\"'.,")

            # Check if there is also an ordinal in target_type, e.g. "first item under Downloads"
            ord_val = None
            type_words = target_type.split()
            if type_words:
                ord_val = parse_ordinal(type_words[0])
                if ord_val is not None:
                    target_type = " ".join(type_words[1:]).strip()

            element_type = None
            group = None
            if target_type in ("button", "input", "icon", "link", "field", "checkbox", "tab"):
                element_type = target_type
            elif target_type in ("option", "search result", "result", "item", "file"):
                group = target_type
            elif target_type:
                element_type = target_type

            return TargetQuery(
                element_type=element_type,
                group=group,
                ordinal=ord_val,
                relation=relation,
                reference=reference,
            )

    # 4. Check for ordinal queries ("second search result", "last option", "third item")
    words = cleaned.split()
    if words:
        first_word = words[0].lower()
        ordinal = parse_ordinal(first_word)
        if ordinal is not None and len(words) > 1:
            rest = " ".join(words[1:]).strip().strip("\"'.,")
            elem_type = rest if rest in ("button", "input", "link", "checkbox", "tab") else None
            return TargetQuery(
                ordinal=ordinal,
                element_type=elem_type,
                group=rest if not elem_type else None,
            )

        if len(words) >= 3:
            first_two = f"{words[0]} {words[1]}".lower()
            ordinal = parse_ordinal(first_two)
            if ordinal is not None:
                rest = " ".join(words[2:]).strip().strip("\"'.,")
                elem_type = rest if rest in ("button", "input", "link", "checkbox", "tab") else None
                return TargetQuery(
                    ordinal=ordinal,
                    element_type=elem_type,
                    group=rest if not elem_type else None,
                )

    # 5. Simple text query
    return TargetQuery(text=cleaned.strip("\"'.,"))
