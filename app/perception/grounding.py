from dataclasses import dataclass

from app.perception.ui_element import UIElement


@dataclass
class GroundingResult:
    found: bool
    element: UIElement | None = None
    score: float = 0.0
    reason: str = ""


class UIGrounder:
    """
    Grounds a natural-language target against perceived UI elements.

    The grounder deliberately avoids matching unrelated or very short
    OCR fragments against longer targets.
    """

    MINIMUM_TARGET_LENGTH = 2
    MINIMUM_CANDIDATE_LENGTH = 2
    MINIMUM_MATCH_SCORE = 0.65

    def find_text(
        self,
        elements,
        target,
        preferred_region=None,
    ):
        if not target or not target.strip():
            return GroundingResult(
                found=False,
                reason="Empty target.",
            )

        target = target.strip()

        candidates = [
            element
            for element in elements
            if self._usable_candidate(element, target)
        ]

        if not candidates:
            return GroundingResult(
                found=False,
                reason=f"No usable UI elements matched target '{target}'.",
            )

        best_result = GroundingResult(
            found=False,
            score=0.0,
            reason="No sufficiently strong match.",
        )

        for element in candidates:
            score, reason = self._score_element(
                element,
                target,
            )

            if preferred_region is not None:
                score, reason = self._apply_region_context(
                    score,
                    reason,
                    element,
                    preferred_region,
                )

            if score > best_result.score:
                best_result = GroundingResult(
                    found=False,
                    element=element,
                    score=score,
                    reason=reason,
                )

        # IMPORTANT:
        # A candidate is not considered found merely because it exists.
        # It must meet the minimum grounding confidence.
        if best_result.score >= self.MINIMUM_MATCH_SCORE:
            best_result.found = True
        else:
            best_result.found = False
            best_result.reason = (
                f"Match score too low: "
                f"{best_result.score:.2f} < "
                f"{self.MINIMUM_MATCH_SCORE:.2f}."
            )

        return best_result

    def ground(
        self,
        elements,
        target,
        preferred_region=None,
    ):
        return self.find_text(
            elements=elements,
            target=target,
            preferred_region=preferred_region,
        )

    def _usable_candidate(
        self,
        element,
        target,
    ):
        candidate_text = str(
            getattr(element, "text", "")
        ).strip()

        candidate_description = str(
            getattr(element, "description", "")
        ).strip()

        candidate_type = str(
            getattr(element, "element_type", "")
        ).strip()

        target_normalized = target.lower().strip()

        candidate_values = [
            candidate_text,
            candidate_description,
            candidate_type,
        ]

        # Prevent single-character OCR fragments such as
        # "O" or "a" from matching longer targets such as "Notepad".
        if len(target_normalized) >= 4:
            if (
                candidate_text
                and len(candidate_text) < self.MINIMUM_CANDIDATE_LENGTH
                and candidate_text.lower() != target_normalized
            ):
                return False

        if candidate_text:
            if not any(
                character.isalnum()
                for character in candidate_text
            ):
                return False

        return any(candidate_values)

    def _score_element(
        self,
        element,
        target,
    ):
        target_normalized = target.strip().lower()

        text = str(
            getattr(element, "text", "")
        ).strip().lower()

        description = str(
            getattr(element, "description", "")
        ).strip().lower()

        element_type = str(
            getattr(element, "element_type", "")
        ).strip().lower()

        confidence = self._apply_confidence_bonus(element)

        # Exact text is the strongest possible match.
        if text == target_normalized:
            return (
                min(1.0, 1.0 + confidence),
                "Exact text match.",
            )

        # Exact semantic description.
        if description == target_normalized:
            return (
                min(1.0, 0.95 + confidence),
                "Exact description match.",
            )

        # Target contained in OCR text.
        if (
            target_normalized in text
            and len(text) >= len(target_normalized)
        ):
            return (
                min(1.0, 0.85 + confidence),
                "Target contained in text.",
            )

        # Target contained in semantic description.
        if (
            target_normalized in description
            and len(description) >= len(target_normalized)
        ):
            return (
                min(1.0, 0.80 + confidence),
                "Target contained in description.",
            )

        # Candidate text contained in target.
        #
        # This is intentionally conservative because OCR can split or
        # partially recognize words.
        if text and len(text) >= 3 and text in target_normalized:
            ratio = len(text) / len(target_normalized)

            if ratio >= 0.50:
                return (
                    min(
                        1.0,
                        0.75 + confidence + (ratio * 0.05),
                    ),
                    "Meaningful candidate contained in target.",
                )

        # Meaningful word overlap.
        target_words = set(
            target_normalized.split()
        )

        candidate_words = set(
            text.split()
        )

        if target_words and candidate_words:
            overlap = (
                len(target_words & candidate_words)
                / len(target_words)
            )

            if overlap >= 0.5:
                return (
                    min(
                        1.0,
                        0.65 + confidence + overlap * 0.05,
                    ),
                    "Meaningful word overlap.",
                )

        # Element type can only be a weak semantic match.
        if (
            element_type
            and element_type == target_normalized
        ):
            return (
                min(1.0, 0.50 + confidence),
                "Element type match.",
            )

        # IMPORTANT:
        # Unrelated candidates must remain below the threshold.
        return (
            confidence,
            "Low-confidence candidate.",
        )

    def _apply_confidence_bonus(
        self,
        element,
    ):
        confidence = float(
            getattr(element, "confidence", 0.0)
        )

        # OCR confidence is commonly 0-100.
        if confidence > 1.0:
            confidence /= 100.0

        confidence = max(
            0.0,
            min(1.0, confidence),
        )

        bonus = min(
            0.03,
            confidence * 0.03,
        )

        if getattr(element, "source", "") == "FUSED":
            bonus += 0.02

        return bonus

    def _apply_region_context(
        self,
        score,
        reason,
        element,
        preferred_region,
    ):
        if self._element_in_region(
            element,
            preferred_region,
        ):
            return score, reason

        return (
            score * 0.50,
            reason + " Outside preferred region.",
        )

    def _element_in_region(
        self,
        element,
        region,
    ):
        if not region:
            return True

        rx, ry, rw, rh = region

        ex = int(
            getattr(element, "x", 0)
        )
        ey = int(
            getattr(element, "y", 0)
        )
        ew = int(
            getattr(element, "width", 0)
        )
        eh = int(
            getattr(element, "height", 0)
        )

        return not (
            ex + ew < rx
            or ey + eh < ry
            or ex > rx + rw
            or ey > ry + rh
        )