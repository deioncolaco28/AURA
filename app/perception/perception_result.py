from dataclasses import dataclass, field

from app.perception.ui_element import UIElement


@dataclass
class PerceptionResult:
    """Unified result of screen perception."""

    elements: list[UIElement] = field(
        default_factory=list
    )

    screen_description: str = ""

    sources_used: list[str] = field(
        default_factory=list
    )

    metadata: dict = field(
        default_factory=dict
    )

    def find_text(
        self,
        text: str,
    ) -> list[UIElement]:
        """Find elements containing text."""

        normalized = text.strip().lower()

        if not normalized:
            return []

        return [
            element
            for element in self.elements
            if element.text
            and normalized
            in element.text.lower()
        ]