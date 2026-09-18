from dataclasses import dataclass, field
from typing import Any

from app.perception.ui_element import UIElement


@dataclass
class ScreenObservation:
    """
    Represents the assistant's current observation of
    the computer screen.

    Fields
    ------
    screen_text : str
        Concatenated visible text from all detected UI elements.
    elements : list[UIElement]
        Perceived UI elements.
    screenshot : Any
        Raw screenshot image (PIL Image or similar).
    metadata : dict
        Arbitrary per-observation context.
    timestamp : float | None
        Unix timestamp of when the observation was captured.
    processes : list[str]
        Running process names at observation time (if available).
    window_title : str | None
        Foreground window title at observation time (if available).
    """

    screen_text: str = ""

    elements: list[UIElement] = field(
        default_factory=list
    )

    screenshot: Any = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    # ------------------------------------------------------------------
    # Optional enrichment fields — all default to None / [] so existing
    # ScreenObservation() construction remains valid.
    # ------------------------------------------------------------------

    #: Unix timestamp of capture (seconds since epoch).
    timestamp: float | None = None

    #: Running process names at observation time.
    processes: list[str] = field(
        default_factory=list
    )

    #: Foreground window title at observation time.
    window_title: str | None = None

    #: Foreground application/process name at observation time.
    foreground_app: str | None = None

    #: Screen dimensions (width, height) in pixels.
    screen_dimensions: tuple[int, int] | None = None

    #: Screen signature (hash or summary of visual/text state).
    screen_signature: str | None = None

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