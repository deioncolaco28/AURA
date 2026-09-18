from dataclasses import dataclass, field
from typing import Any


@dataclass
class UIElement:
    """Represents a unified UI element detected on the screen."""

    element_id: str
    element_type: str

    text: str | None = None
    description: str | None = None

    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

    confidence: float = 0.0
    source: str = "unknown"

    attributes: dict[str, Any] = field(
        default_factory=dict
    )

    # ------------------------------------------------------------------
    # Optional derived / enrichment fields
    #
    # These are populated by perception enrichment passes (e.g. the
    # SpatialReasoner or PerceptionManager).  All default to None so
    # that existing UIElement construction sites remain valid without
    # any changes.
    # ------------------------------------------------------------------

    #: Semantic role within the UI (e.g. "search_result", "menu_item").
    semantic_role: str | None = None

    #: Candidate group label (e.g. "button", "list_item", "option").
    group: str | None = None

    #: Row index within a detected grid/table (0-based, None if unknown).
    row: int | None = None

    #: Column index within a detected grid/table (0-based, None if unknown).
    column: int | None = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def center(self) -> tuple[int, int]:
        return (
            self.x + self.width // 2,
            self.y + self.height // 2,
        )

    @property
    def bounds(self) -> tuple[int, int, int, int]:
        return (
            self.x,
            self.y,
            self.width,
            self.height,
        )

    def has_text(self) -> bool:
        return bool(
            self.text
            and self.text.strip()
        )

    def has_description(self) -> bool:
        return bool(
            self.description
            and self.description.strip()
        )