from dataclasses import dataclass

from app.perception.ui_element import UIElement


@dataclass
class GroundingResult:
    """Represents a grounded UI target."""

    target: str
    element: UIElement | object | None
    score: float
    reason: str

    @property
    def found(self) -> bool:
        """Return whether a target was grounded."""

        return self.element is not None


class UIGrounder:
    """
    Finds the best UI element for a natural-language target.

    Grounding considers:

    1. Exact text
    2. Text containment
    3. Description
    4. Word overlap
    5. Element confidence
    6. Fused OCR/VLM elements
    7. Optional preferred screen region

    The grounder remains compatible with both:
        - UIElement
        - legacy OCR TextElement
    """

    def find_text(
        self,
        elements,
        target: str,
        preferred_region=None,
    ):
        """Find a matching UI element."""

        result = self.ground(
            elements,
            target,
            preferred_region=preferred_region,
        )

        return result.element

    def ground(
        self,
        elements,
        target: str,
        preferred_region=None,
    ) -> GroundingResult:
        """
        Find the best matching element.

        preferred_region:
            Optional tuple:
                (x, y, width, height)

            When supplied, elements outside this region
            receive a penalty. This is useful for tutoring
            scenarios where the relevant UI area is known.
        """

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

            if preferred_region is not None:
                score, reason = (
                    self._apply_region_context(
                        score,
                        reason,
                        element,
                        preferred_region,
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
        """Score one UI element against a target."""

        candidates = []

        text = getattr(
            element,
            "text",
            None,
        )

        description = getattr(
            element,
            "description",
            None,
        )

        attributes = getattr(
            element,
            "attributes",
            {},
        )

        if text:
            candidates.append(
                (
                    text,
                    "text",
                )
            )

        if description:
            candidates.append(
                (
                    description,
                    "description",
                )
            )

        if attributes:
            attribute_description = (
                attributes.get(
                    "description"
                )
            )

            if attribute_description:
                candidates.append(
                    (
                        attribute_description,
                        "attribute description",
                    )
                )

        best_score = 0.0
        best_reason = "No meaningful match."

        for candidate, source in candidates:

            normalized_candidate = (
                self._normalize(
                    candidate
                )
            )

            if not normalized_candidate:
                continue

            if (
                normalized_candidate
                == target
            ):
                score = 1.0

                element_source = getattr(
                    element,
                    "source",
                    None,
                )

                if element_source == "FUSED":
                    reason = (
                        f"Exact {source} match "
                        "from fused perception."
                    )
                else:
                    reason = (
                        f"Exact {source} match."
                    )

                score = (
                    self._apply_confidence_bonus(
                        score,
                        element,
                    )
                )

                if score > best_score:
                    best_score = score
                    best_reason = reason

                continue

            if target in normalized_candidate:

                score = 0.85

                score = (
                    self._apply_confidence_bonus(
                        score,
                        element,
                    )
                )

                if score > best_score:
                    best_score = score
                    best_reason = (
                        f"Target contained in "
                        f"{source}."
                    )

                continue

            if normalized_candidate in target:

                score = 0.75

                score = (
                    self._apply_confidence_bonus(
                        score,
                        element,
                    )
                )

                if score > best_score:
                    best_score = score
                    best_reason = (
                        f"{source.capitalize()} "
                        "contained in target."
                    )

                continue

            target_words = set(
                target.split()
            )

            candidate_words = set(
                normalized_candidate.split()
            )

            if (
                target_words
                and candidate_words
            ):

                overlap = (
                    len(
                        target_words
                        & candidate_words
                    )
                    / len(
                        target_words
                        | candidate_words
                    )
                )

                if overlap >= 0.5:

                    score = 0.65

                    score = (
                        self._apply_confidence_bonus(
                            score,
                            element,
                        )
                    )

                    if score > best_score:
                        best_score = score
                        best_reason = (
                            f"Strong word overlap "
                            f"in {source}."
                        )

        return (
            min(best_score, 1.0),
            best_reason,
        )

    def _apply_region_context(
        self,
        score: float,
        reason: str,
        element,
        preferred_region,
    ) -> tuple[float, str]:
        """
        Apply optional spatial context.

        Elements inside the preferred region retain
        their original score.

        Elements outside the preferred region receive
        a penalty so that an equally good match inside
        the relevant region is preferred.
        """

        if self._element_in_region(
            element,
            preferred_region,
        ):
            return (
                score,
                f"{reason} Preferred region match.",
            )

        # Strongly reduce unrelated matches while
        # preserving the element as a possible fallback.
        adjusted_score = score * 0.50

        return (
            adjusted_score,
            f"{reason} Outside preferred region.",
        )

    @staticmethod
    def _element_in_region(
        element,
        region,
    ) -> bool:
        """
        Check whether an element overlaps the preferred
        region.

        region = (x, y, width, height)
        """

        if not region or len(region) != 4:
            return True

        rx, ry, rw, rh = region

        ex = int(
            getattr(element, "x", 0)
            or 0
        )
        ey = int(
            getattr(element, "y", 0)
            or 0
        )
        ew = int(
            getattr(element, "width", 0)
            or 0
        )
        eh = int(
            getattr(element, "height", 0)
            or 0
        )

        element_left = ex
        element_top = ey
        element_right = ex + ew
        element_bottom = ey + eh

        region_left = rx
        region_top = ry
        region_right = rx + rw
        region_bottom = ry + rh

        return (
            element_right > region_left
            and element_left < region_right
            and element_bottom > region_top
            and element_top < region_bottom
        )

    def _apply_confidence_bonus(
        self,
        score: float,
        element,
    ) -> float:
        """
        Slightly reward high-confidence perception.

        Supports both UIElement and legacy OCR
        TextElement objects.
        """

        confidence = float(
            getattr(
                element,
                "confidence",
                0.0,
            )
            or 0.0
        )

        # OCR confidence may be represented as a
        # percentage such as 95.0 rather than 0-1.
        if confidence > 1.0:
            confidence /= 100.0

        if confidence >= 0.90:
            score += 0.03

        elif confidence >= 0.75:
            score += 0.02

        if getattr(
            element,
            "source",
            None,
        ) == "FUSED":
            score += 0.02

        return min(
            score,
            1.0,
        )

    @staticmethod
    def _normalize(
        text: str | None,
    ) -> str:
        if not text:
            return ""

        return " ".join(
            text.strip().lower().split()
        )