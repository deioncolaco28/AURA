from dataclasses import dataclass

from app.perception.ocr import TextElement
from app.perception.ui_element import UIElement


@dataclass
class GroundingResult:
    """Represents a grounded UI target."""

    target: str
    element: UIElement | TextElement | None
    score: float
    reason: str

    @property
    def found(self) -> bool:
        """Return whether a target was grounded."""

        return self.element is not None


class UIGrounder:
    """Finds UI elements using text and descriptions."""

    def find_text(
        self,
        elements,
        target: str,
    ):
        """Find a matching UI element."""

        result = self.ground(
            elements,
            target,
        )

        return result.element

    def ground(
        self,
        elements,
        target: str,
    ) -> GroundingResult:
        """Find the best matching element."""

        normalized_target = self._normalize(
            target
        )

        if not normalized_target:
            return GroundingResult(
                target=target,
                element=None,
                score=0.0,
                reason="Target is empty.",
            )

        best_element = None
        best_score = 0.0
        best_reason = ""

        for element in elements:
            score, reason = (
                self._score_element(
                    element,
                    normalized_target,
                )
            )

            if score > best_score:
                best_element = element
                best_score = score
                best_reason = reason

        if best_element is None:
            return GroundingResult(
                target=target,
                element=None,
                score=0.0,
                reason="No suitable match found.",
            )

        return GroundingResult(
            target=target,
            element=best_element,
            score=best_score,
            reason=best_reason,
        )

    def _score_element(
        self,
        element,
        target: str,
    ) -> tuple[float, str]:
        """Score an element against a target."""

        candidates = []

        if getattr(
            element,
            "text",
            None,
        ):
            candidates.append(
                element.text
            )

        if getattr(
            element,
            "attributes",
            None,
        ):
            description = (
                element.attributes.get(
                    "description"
                )
            )

            if description:
                candidates.append(
                    description
                )

        if hasattr(
            element,
            "description",
        ):
            if element.description:
                candidates.append(
                    element.description
                )

        best_score = 0.0
        best_reason = "No meaningful match."

        for candidate in candidates:
            text = self._normalize(
                candidate
            )

            if text == target:
                return (
                    1.0,
                    "Exact match.",
                )

            if target in text:
                best_score = max(
                    best_score,
                    0.85,
                )
                best_reason = (
                    "Target contained in element."
                )
                continue

            if text in target:
                best_score = max(
                    best_score,
                    0.75,
                )
                best_reason = (
                    "Element text contained in target."
                )
                continue

            target_words = set(
                target.split()
            )

            text_words = set(
                text.split()
            )

            if target_words and text_words:
                overlap = (
                    len(
                        target_words
                        & text_words
                    )
                    / len(
                        target_words
                        | text_words
                    )
                )

                if overlap >= 0.5:
                    best_score = max(
                        best_score,
                        0.65,
                    )
                    best_reason = (
                        "Strong word overlap."
                    )

        return (
            best_score,
            best_reason,
        )

    def _normalize(
        self,
        text: str,
    ) -> str:
        """Normalize text for matching."""

        return " ".join(
            text.strip().lower().split()
        )