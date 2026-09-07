from dataclasses import dataclass, field
from typing import Any


@dataclass
class UIElement:
    """Represents a unified UI element."""

    element_id: str

    element_type: str

    text: str | None = None

    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

    confidence: float = 0.0

    source: str = "unknown"

    attributes: dict[str, Any] = field(
        default_factory=dict
    )

    @property
    def center(self) -> tuple[int, int]:
        """Return the center coordinates."""

        return (
            self.x + self.width // 2,
            self.y + self.height // 2,
        )

    @property
    def bounds(self) -> tuple[int, int, int, int]:
        """Return element bounds."""

        return (
            self.x,
            self.y,
            self.width,
            self.height,
        )