"""
app/perception/perception_result.py

Unified result produced by AURA's perception layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.perception.ui_element import UIElement

if TYPE_CHECKING:
    from app.perception.ui_graph import UIElementGraph


@dataclass
class PerceptionResult:
    """
    Unified result produced by AURA's perception layer.

    Accessibility, DOM, OCR and VLM outputs are converted into UIElement objects
    and fused into one normalized representation with an attached UIElementGraph.
    """

    elements: list[UIElement] = field(
        default_factory=list
    )

    screen_description: str = ""

    sources_used: list[str] = field(
        default_factory=list
    )

    screenshot: Any = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    ui_graph: Any = None
    overall_confidence: float = 0.0

    @property
    def element_count(self) -> int:
        """Return the number of unified UI elements."""
        return len(self.elements)

    @property
    def has_elements(self) -> bool:
        """Return True when UI elements were detected."""
        return bool(self.elements)

    def get_elements_by_source(
        self,
        source: str,
    ) -> list[UIElement]:
        """Return elements originating from a source."""
        return [
            element
            for element in self.elements
            if element.source == source or source in element.source
        ]

    def contains_text(
        self,
        text: str,
    ) -> bool:
        """Return True when an element contains the requested text."""
        if not text:
            return False

        normalized = text.strip().lower()

        return any(
            normalized in (
                element.text or ""
            ).lower()
            for element in self.elements
        )