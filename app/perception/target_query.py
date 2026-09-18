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


def parse_target_query(phrase: str) -> TargetQuery:
    """
    Parse a natural language target phrase or instruction into a structured TargetQuery.

    Supports:
        - Ordinals: "second search result", "last option", "third item", "first result", "second-last option"
        - Directional: "option below Calculator", "item above Notepad", "button to the right of Search"
        - Proximity: "nearest result", "item next to Calculator", "option beside Calculator"
        - Plain text: "Notepad", "Calculator"
    """
    if not phrase or not phrase.strip():
        return TargetQuery()

    cleaned = phrase.strip()

    # Remove conversational command prefixes like "click the", "click", "select", etc.
    prefixes_to_strip = [
        "click on the ", "click the ", "click ",
        "select the ", "select ",
        "choose the ", "choose ",
        "press the ", "press ",
        "tap the ", "tap ",
        "the ",
    ]
    cleaned_lower = cleaned.lower()
    for prefix in prefixes_to_strip:
        if cleaned_lower.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
            cleaned_lower = cleaned.lower()
            break

    # 1. Check for spatial relationships (relational queries)
    # Patterns: "<type> below/above/left of/right of/next to/beside/near <reference>"
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

            # Extract any element_type or group from prefix
            element_type = None
            group = None
            if target_type in ("button", "input", "icon", "link", "field"):
                element_type = target_type
            elif target_type in ("option", "search result", "result", "item"):
                group = target_type

            return TargetQuery(
                element_type=element_type,
                group=group,
                relation=relation,
                reference=reference,
            )

    # 2. Check for ordinal queries ("second search result", "last option", "third item")
    words = cleaned.split()
    if words:
        first_word = words[0].lower()
        ordinal = parse_ordinal(first_word)
        if ordinal is not None and len(words) > 1:
            rest = " ".join(words[1:]).strip().strip("\"'.,")
            return TargetQuery(
                ordinal=ordinal,
                group=rest,
            )

        # Multi-word ordinals: "second last option", "second-last option"
        if len(words) >= 3:
            first_two = f"{words[0]} {words[1]}".lower()
            ordinal = parse_ordinal(first_two)
            if ordinal is not None:
                rest = " ".join(words[2:]).strip().strip("\"'.,")
                return TargetQuery(
                    ordinal=ordinal,
                    group=rest,
                )

    # 3. Simple text query
    return TargetQuery(text=cleaned.strip("\"'.,"))
