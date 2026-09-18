"""
app/perception/ui_element.py

Canonical representation of perceived UI elements across all perception sources
(Accessibility, DOM, OCR, VLM, and fused perception).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any


def generate_stable_id(
    element_type: str | None = None,
    text: str | None = None,
    x: int = 0,
    y: int = 0,
    width: int = 0,
    height: int = 0,
    source: str = "unknown",
    app_name: str | None = None,
    quantize_px: int = 10,
) -> str:
    """
    Generate a deterministic, stable element identifier across perception passes.

    Quantizes coordinates to absorb minor sub-pixel or rendering jitter.
    Incorporates normalized text, element type, and application context.
    """
    clean_type = (element_type or "elem").lower().strip()
    clean_text = ""
    if text:
        clean_text = re.sub(r"\s+", "_", text.strip().lower())[:24]

    # Quantize geometry to avoid jitter across frame captures
    qx = (x // quantize_px) * quantize_px
    qy = (y // quantize_px) * quantize_px
    qw = (width // quantize_px) * quantize_px
    qh = (height // quantize_px) * quantize_px

    raw_signature = f"{clean_type}:{clean_text}:{qx}:{qy}:{qw}:{qh}:{app_name or ''}"
    sig_hash = hashlib.sha256(raw_signature.encode("utf-8")).hexdigest()[:8]

    if clean_text:
        return f"{clean_type}_{clean_text}_{sig_hash}"
    return f"{clean_type}_{qx}_{qy}_{sig_hash}"


@dataclass
class UIElement:
    """Represents a unified, canonical UI element detected on the screen."""

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
    # State & Interactive properties
    # ------------------------------------------------------------------
    is_enabled: bool = True
    is_selected: bool = False
    is_focused: bool = False
    is_interactable: bool = True

    # ------------------------------------------------------------------
    # Hierarchy & Structure
    # ------------------------------------------------------------------
    parent_id: str | None = None
    children_ids: list[str] = field(default_factory=list)

    #: Candidate group label (e.g. "button", "list_item", "option").
    group: str | None = None

    #: Semantic role within the UI (e.g. "search_result", "menu_item").
    semantic_role: str | None = None

    #: Row index within a detected grid/table (0-based, None if unknown).
    row: int | None = None

    #: Column index within a detected grid/table (0-based, None if unknown).
    column: int | None = None

    #: Screen region (e.g. "top", "bottom", "left", "right", "center").
    screen_region: str | None = None

    # ------------------------------------------------------------------
    # Application Context
    # ------------------------------------------------------------------
    app_name: str | None = None
    window_title: str | None = None
    stable_id: str | None = None

    def __post_init__(self):
        if self.stable_id is None:
            self.stable_id = generate_stable_id(
                element_type=self.element_type,
                text=self.text,
                x=self.x,
                y=self.y,
                width=self.width,
                height=self.height,
                source=self.source,
                app_name=self.app_name,
            )

    # ------------------------------------------------------------------
    # Properties & Helper Methods
    # ------------------------------------------------------------------

    @property
    def id(self) -> str:
        return self.element_id

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

    @property
    def area(self) -> int:
        return max(0, self.width) * max(0, self.height)

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

    def contains_point(self, px: int, py: int) -> bool:
        """Check if point (px, py) is inside element bounds."""
        return (
            self.x <= px <= self.x + self.width
            and self.y <= py <= self.y + self.height
        )

    def is_similar_to(self, other: UIElement, position_tolerance: int = 30) -> bool:
        """Check if this element is likely the same as another observed element."""
        if not isinstance(other, UIElement):
            return False

        if self.stable_id and other.stable_id and self.stable_id == other.stable_id:
            return True

        if self.has_text() and other.has_text():
            if self.text.strip().lower() == other.text.strip().lower():
                dx = abs(self.center[0] - other.center[0])
                dy = abs(self.center[1] - other.center[1])
                return dx <= position_tolerance and dy <= position_tolerance

        return False


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
            is_enabled=bool(element.get("is_enabled", True)),
            is_selected=bool(element.get("is_selected", False)),
            is_focused=bool(element.get("is_focused", False)),
            is_interactable=bool(element.get("is_interactable", True)),
            parent_id=element.get("parent_id"),
            children_ids=list(element.get("children_ids", [])),
            app_name=element.get("app_name"),
            window_title=element.get("window_title"),
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
        is_enabled=getattr(element, "is_enabled", True),
        is_selected=getattr(element, "is_selected", False),
        is_focused=getattr(element, "is_focused", False),
        is_interactable=getattr(element, "is_interactable", True),
        parent_id=getattr(element, "parent_id", None),
        children_ids=getattr(element, "children_ids", []),
        app_name=getattr(element, "app_name", None),
        window_title=getattr(element, "window_title", None),
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