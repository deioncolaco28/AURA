"""
app/tutoring/tutoring_engine.py

Perception and target-resolution engine for SHOW_ME_HOW mode.

Responsibilities
----------------
- Capture the screen.
- Run OCR (and optionally VLM) perception.
- Identify candidate UI elements.
- Use SpatialReasoner for candidate ordering.
- Use TargetRanker to select the best candidate.
- Return a RankedCandidate with a human-readable description.

Non-responsibilities
--------------------
- Performing the user's requested action (never).
- Clicking, typing, or pressing keys (never).
- Speaking instructions (owned by TutoringController).
- Requiring HighlightOverlay (optional — injected for backwards compat).
"""

from __future__ import annotations

from app.intelligence.target_ranker import RankedCandidate, TargetRanker
from app.perception.grounding import UIGrounder
from app.perception.ocr import OCR, TesseractOCR
from app.perception.screenshot import ScreenshotCapture
from app.perception.spatial_reasoner import SpatialReasoner
from app.perception.target_query import TargetQuery
from app.perception.ui_element import to_ui_elements
from app.tutoring.instruction import TutoringInstruction


class TutoringEngine:
    """
    Provides lower-level tutoring perception services.

    The TutoringController owns the tutoring workflow and speech.

    This engine is responsible for:
        - capturing the screen
        - detecting visible targets
        - grounding / spatially reasoning about targets
        - ranking candidates
        - returning the best candidate with explanation

    It never:
        - speaks
        - clicks
        - types
        - presses keys
        - performs the user's requested action
        - REQUIRES the HighlightOverlay (overlay is optional)
    """

    def __init__(
        self,
        voice_manager=None,
        screenshot_capture: ScreenshotCapture | None = None,
        ocr: OCR | None = None,
        grounder: UIGrounder | None = None,
        overlay=None,
        target_ranker: TargetRanker | None = None,
        spatial_reasoner: SpatialReasoner | None = None,
    ):
        # Kept for backwards compatibility with existing callers/tests.
        self.voice_manager = voice_manager

        self.screenshot_capture = (
            screenshot_capture
            or ScreenshotCapture()
        )

        self.ocr = (
            ocr
            or TesseractOCR()
        )

        self.grounder = (
            grounder
            or UIGrounder()
        )

        # Overlay is OPTIONAL.  When absent, the engine works correctly.
        self.overlay = overlay  # may be None

        self.target_ranker = (
            target_ranker
            or TargetRanker()
        )

        self.spatial_reasoner = (
            spatial_reasoner
            or SpatialReasoner()
        )

    # ------------------------------------------------------------------
    # Core perception method
    # ------------------------------------------------------------------

    def locate_target(
        self,
        target: str,
        query: TargetQuery | None = None,
    ) -> RankedCandidate | None:
        """
        Locate the best candidate element for a target label.

        Parameters
        ----------
        target : str
            Text label to locate.
        query : TargetQuery | None
            Optional structured query for spatial/ordinal resolution.

        Returns
        -------
        RankedCandidate | None
            The best-ranked candidate, or None when not found.
        """

        if not target and query is None:
            return None

        try:
            image = self.screenshot_capture.capture()
            elements = to_ui_elements(self.ocr.detect_text(image))

            if not elements:
                return None

            if query is not None:
                # Use structured query resolution.
                grounding_result = self.grounder.ground_with_query(
                    elements, query
                )
            else:
                # Fall back to plain text grounding.
                grounding_result = self.grounder.ground(
                    elements, target
                )

            if not grounding_result.found or grounding_result.element is None:
                return None

            # Build a spatial score map for the ranker.
            spatial_scores = {
                grounding_result.element.element_id: grounding_result.score
            }

            effective_query = query or TargetQuery(text=target)

            ranking_result = self.target_ranker.rank(
                elements=[grounding_result.element],
                query=effective_query,
                spatial_scores=spatial_scores,
            )

            if not ranking_result.found:
                return None

            return ranking_result.best

        except Exception as error:
            print(
                f"TutoringEngine: locate_target error: {error}"
            )
            return None

    def describe_target(
        self,
        target: str,
        query: TargetQuery | None = None,
    ) -> str:
        """
        Return a human-readable description of where the target is.

        Examples:
            "Notepad"
            "the second search result, Notepad"
            "the option below Calculator"

        Falls back to the raw target label when perception is unavailable.
        """

        candidate = self.locate_target(target, query)

        if candidate is None:
            return target

        element = candidate.element
        label = (
            str(element.text or "").strip()
            or str(element.description or "").strip()
            or target
        )

        if query and query.has_ordinal:
            from app.perception.spatial_reasoner import _ordinal_label

            if query.ordinal is not None:
                ordinal_word = _ordinal_label(query.ordinal, 99)
                return f"the {ordinal_word} item, {label}"

        if query and query.has_relation:
            return (
                f"the item {query.relation} {query.reference}, {label}"
            )

        return label

    # ------------------------------------------------------------------
    # Compatibility method (backwards compat with existing callers/tests)
    # ------------------------------------------------------------------

    def guide(
        self,
        instruction: TutoringInstruction,
    ) -> bool:
        """
        Compatibility method for older callers.

        Returns True when the target can be located
        (or when there is no target to locate).

        Does NOT require overlay.
        """

        if instruction.target:
            candidate = self.locate_target(
                instruction.target,
                instruction.target_query,
            )
            return candidate is not None

        return True

    def highlight_target(
        self,
        target: str,
    ) -> bool:
        """
        Locate and optionally highlight a visible UI target.

        When an overlay is injected, it will be shown.
        When no overlay is configured, this method still returns True
        if the target can be located (perception-only mode).

        Returns True when a sufficiently reliable target was found.
        This method NEVER performs the user's requested action.
        """

        if not target or not target.strip():
            return False

        try:
            image = self.screenshot_capture.capture()
            elements = to_ui_elements(self.ocr.detect_text(image))
            result = self.grounder.ground(
                elements=elements,
                target=target,
            )

            if not result.found:
                print(
                    f"Could not find tutoring target: "
                    f"{target}"
                )
                return False

            if result.score < 0.65:
                print(
                    f"Target match too weak: "
                    f"{target} "
                    f"(score={result.score:.2f})"
                )
                return False

            element = result.element

            print(
                f"Grounded tutoring target: "
                f"{element.text} "
                f"score={result.score:.2f} "
                f"reason={result.reason}"
            )

            # Show overlay only when one is available.
            if self.overlay is not None:
                try:
                    self.overlay.show(
                        x=element.x,
                        y=element.y,
                        width=element.width,
                        height=element.height,
                    )
                except Exception as overlay_error:
                    print(
                        f"Overlay failed (non-fatal): "
                        f"{overlay_error}"
                    )

            return True

        except Exception as error:
            print(
                f"Tutoring target detection error: "
                f"{error}"
            )
            return False

    def clear_highlight(self) -> None:
        """Remove the current tutoring highlight (if overlay is active)."""

        if self.overlay is not None:
            try:
                self.overlay.close()
            except Exception:
                pass