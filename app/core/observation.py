from dataclasses import dataclass, field
from typing import Any

from app.perception.ui_element import UIElement


@dataclass
class ScreenObservation:
    """
    Represents the assistant's current observation of
    the computer screen.
    """

    screen_text: str = ""

    elements: list[UIElement] = field(
        default_factory=list
    )

    screenshot: Any = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    @property
    def has_text(self) -> bool:
        """Return True when screen text is available."""

        return bool(
            self.screen_text.strip()
        )

    @property
    def element_count(self) -> int:
        """Return the number of detected UI elements."""

        return len(self.elements)

    def contains_text(
        self,
        text: str,
    ) -> bool:
        """Check whether the observed screen contains text."""

        if not text:
            return False

        return (
            text.lower()
            in self.screen_text.lower()
        )