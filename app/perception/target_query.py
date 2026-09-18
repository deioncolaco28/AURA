"""
app/perception/target_query.py

Structured representation of a user's target request.

A TargetQuery captures the *intent* behind a target reference so
that the spatial reasoner and target ranker can resolve it against
actual perceived UI elements without application-specific hard-coding.

Examples
--------
"second search result"
    TargetQuery(group="search_result", ordinal=2)

"last option"
    TargetQuery(group="option", ordinal=-1)

"option below Calculator"
    TargetQuery(group="option", relation="below", reference="Calculator")

"button to the right of Search"
    TargetQuery(element_type="button", relation="right", reference="Search")

"Notepad"
    TargetQuery(text="Notepad")
"""

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


# ---------------------------------------------------------------------------
# TargetQuery
# ---------------------------------------------------------------------------


@dataclass
class TargetQuery:
    """
    Structured query representing what UI element the user means.

    Fields
    ------
    text : str | None
        Literal text label to match (e.g. "Notepad", "Search").

    element_type : str | None
        Element type filter (e.g. "button", "input", "list_item").

    ordinal : int | None
        1-based ordinal for positive values (1 = first, 2 = second).
        Negative values count from the end (-1 = last, -2 = second-last).

    relation : str | None
        Spatial relation to a reference element.
        One of: "above", "below", "left", "right", "nearest", "beside".

    reference : str | None
        Text label of the reference element for relational queries.

    group : str | None
        Semantic group of candidate elements
        (e.g. "search_result", "menu_option", "button").

    region : str | None
        Screen region hint: "top", "bottom", "left", "right", "center".

    metadata : dict
        Arbitrary extra context for extensibility.
    """

    text: str | None = None
    element_type: str | None = None
    ordinal: int | None = None
    relation: str | None = None
    reference: str | None = None
    group: str | None = None
    region: str | None = None
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

    # ------------------------------------------------------------------
    # Human-readable summary
    # ------------------------------------------------------------------

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

        if self.element_type:
            parts.append(self.element_type)

        if self.group:
            parts.append(self.group)

        if self.text:
            parts.append(f'"{self.text}"')

        if self.relation and self.reference:
            parts.append(
                f"{self.relation} {self.reference}"
            )

        if self.region:
            parts.append(f"in {self.region}")

        if not parts:
            return "unspecified target"

        return " ".join(parts)


# ---------------------------------------------------------------------------
# Simple parser for natural-language ordinal phrases
# ---------------------------------------------------------------------------


def parse_ordinal(text: str) -> int | None:
    """
    Parse a natural-language ordinal string into an integer.

    Returns None when the string is not a recognised ordinal.

    Examples
    --------
    >>> parse_ordinal("first")
    1
    >>> parse_ordinal("last")
    -1
    >>> parse_ordinal("second-last")
    -2
    >>> parse_ordinal("3rd")
    3
    """

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

    # Numeric ordinals: "2nd", "3rd", "4th", ...
    for suffix in ("st", "nd", "rd", "th"):
        if text.endswith(suffix):
            numeric_part = text[: -len(suffix)]
            try:
                return int(numeric_part)
            except ValueError:
                pass

    # Plain integer
    try:
        return int(text)
    except ValueError:
        return None
