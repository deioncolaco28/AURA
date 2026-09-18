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

    #: Screen region (e.g. "top", "bottom", "left", "right", "center").
    screen_region: str | None = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def group_id(self) -> str | None:
        """Alias for group."""
        return self.group

    @group_id.setter
    def group_id(self, value: str | None) -> None:
        self.group = value

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


def as_ui_element(element: Any, index: int = 0) -> UIElement:
    """
    Safely convert any perception element (UIElement, TextElement, VLMElement, dict)
    into a canonical UIElement.
    """
    if isinstance(element, UIElement):
        if not element.element_id:
            element.element_id = f"elem-{index}"
        return element

    # Check if element is a dictionary
    if isinstance(element, dict):
        conf = float(element.get("confidence", 1.0))
        if conf > 1.0:
            conf = conf / 100.0
        return UIElement(
            element_id=str(element.get("element_id") or f"elem-{index}"),
            element_type=str(element.get("element_type", "unknown")),
            text=element.get("text"),
            description=element.get("description"),
            x=int(element.get("x", 0)),
            y=int(element.get("y", 0)),
            width=int(element.get("width", 0)),
            height=int(element.get("height", 0)),
            confidence=max(0.0, min(1.0, conf)),
            source=str(element.get("source", "dict")),
            attributes=dict(element.get("attributes", {})),
        )

    # TextElement / VLMElement or similar duck-typed object
    text = getattr(element, "text", None)
    description = getattr(element, "description", None)
    x = int(getattr(element, "x", 0))
    y = int(getattr(element, "y", 0))
    width = int(getattr(element, "width", 0))
    height = int(getattr(element, "height", 0))
    raw_conf = getattr(element, "confidence", 1.0)
    try:
        conf = float(raw_conf)
        if conf > 1.0:
            conf = conf / 100.0
        conf = max(0.0, min(1.0, conf))
    except (ValueError, TypeError):
        conf = 0.5

    element_type = getattr(element, "element_type", "text" if text else "unknown")
    source = getattr(element, "source", "OCR" if hasattr(element, "confidence") and not description else "unknown")
    element_id = getattr(element, "element_id", None) or f"{source.lower()}-{index}"

    return UIElement(
        element_id=element_id,
        element_type=element_type,
        text=text,
        description=description,
        x=x,
        y=y,
        width=width,
        height=height,
        confidence=conf,
        source=source,
        attributes=getattr(element, "attributes", {}),
    )


def to_ui_elements(elements: Any) -> list[UIElement]:
    """
    Convert an iterable of elements into a list of canonical UIElements.
    """
    if not elements:
        return []

    return [
        as_ui_element(elem, index=i)
        for i, elem in enumerate(elements)
    ]