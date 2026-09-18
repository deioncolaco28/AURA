from dataclasses import dataclass, field
from typing import Any

from app.core.observation_diff import ObservationDiffer
from app.perception.grounding import UIGrounder
from app.perception.ocr import OCR, TesseractOCR
from app.perception.screenshot import ScreenshotCapture


@dataclass
class ScreenVerificationResult:
    success: bool
    message: str = ""
    verification_type: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    detected_text: list[str] = field(default_factory=list)

    def __bool__(self):
        return self.success

    @property
    def passed(self):
        return self.success


class ScreenVerifier:
    """
    Verifies screen state using screenshot capture, OCR and UI grounding.
    """

    def __init__(
        self,
        screenshot_capture: ScreenshotCapture | None = None,
        ocr: OCR | None = None,
        grounder: UIGrounder | None = None,
    ):
        self.screenshot_capture = (
            screenshot_capture or ScreenshotCapture()
        )
        self.ocr = ocr or TesseractOCR()
        self.grounder = grounder or UIGrounder()

    def contains_text(self, target: str) -> ScreenVerificationResult:
        if not target or not target.strip():
            return ScreenVerificationResult(
                success=False,
                message="Target text cannot be empty.",
                verification_type="SCREEN_CONTAINS_TEXT",
            )

        image = self.screenshot_capture.capture()
        elements = self.ocr.detect_text(image)

        detected_text = [
            str(getattr(element, "text", "")).strip()
            for element in elements
            if str(getattr(element, "text", "")).strip()
        ]

        result = self.grounder.ground(
            elements=elements,
            target=target,
        )

        if result.found:
            return ScreenVerificationResult(
                success=True,
                message=f"Found '{target}' on the screen.",
                verification_type="SCREEN_CONTAINS_TEXT",
                detected_text=detected_text,
                metadata={
                    "grounding_score": result.score,
                    "grounding_reason": result.reason,
                },
            )

        return ScreenVerificationResult(
            success=False,
            message=f"Could not find '{target}' on the screen.",
            verification_type="SCREEN_CONTAINS_TEXT",
            detected_text=detected_text,
        )

    def does_not_contain_text(
        self,
        target: str,
    ) -> ScreenVerificationResult:
        if not target or not target.strip():
            return ScreenVerificationResult(
                success=True,
                message="Target text is empty.",
                verification_type="SCREEN_DOES_NOT_CONTAIN_TEXT",
            )

        image = self.screenshot_capture.capture()
        elements = self.ocr.detect_text(image)

        detected_text = [
            str(getattr(element, "text", "")).strip()
            for element in elements
            if str(getattr(element, "text", "")).strip()
        ]

        result = self.grounder.ground(
            elements=elements,
            target=target,
        )

        if result.found:
            return ScreenVerificationResult(
                success=False,
                message=f"Found '{target}' on the screen.",
                verification_type="SCREEN_DOES_NOT_CONTAIN_TEXT",
                detected_text=detected_text,
                metadata={
                    "grounding_score": result.score,
                    "grounding_reason": result.reason,
                },
            )

        return ScreenVerificationResult(
            success=True,
            message=f"'{target}' was not found on the screen.",
            verification_type="SCREEN_DOES_NOT_CONTAIN_TEXT",
            detected_text=detected_text,
        )

    def has_screen_changed(
        self,
        baseline,
    ) -> ScreenVerificationResult:
        if baseline is None:
            return ScreenVerificationResult(
                success=False,
                message="Baseline screenshot is unavailable.",
                verification_type="SCREEN_CHANGED",
            )

        current = self.screenshot_capture.capture()

        try:
            from PIL import ImageChops

            difference = ImageChops.difference(
                baseline,
                current,
            )

            changed = difference.getbbox() is not None

            return ScreenVerificationResult(
                success=changed,
                message=(
                    "Screen changed."
                    if changed
                    else "Screen did not change."
                ),
                verification_type="SCREEN_CHANGED",
            )

        except Exception as error:
            return ScreenVerificationResult(
                success=False,
                message=f"Screen comparison failed: {error}",
                verification_type="SCREEN_CHANGED",
            )

    def verify(self, action) -> ScreenVerificationResult:
        verification = getattr(action, "verification", {})

        if not isinstance(verification, dict):
            verification = {}

        verification_type = verification.get("type")

        if verification_type == "SCREEN_CONTAINS_TEXT":
            target = verification.get("text") or action.value
            return self.contains_text(str(target))

        if verification_type == "SCREEN_DOES_NOT_CONTAIN_TEXT":
            target = verification.get("text") or action.value
            return self.does_not_contain_text(str(target))

        if verification_type == "SCREEN_CHANGED":
            baseline = verification.get("baseline")
            return self.has_screen_changed(baseline)

        return ScreenVerificationResult(
            success=True,
            message="No screen verification required.",
            verification_type=verification_type,
        )

    def verify_transition(
        self,
        before,
        after,
        expected: dict,
    ) -> ScreenVerificationResult:
        """
        Verify that the expected state transition occurred between
        two ScreenObservation instances.

        This method distinguishes:
            TARGET FOUND (presence alone)
            vs
            ACTION CAUSED EXPECTED STATE (actual transition)

        Parameters
        ----------
        before : ScreenObservation
            Baseline observation captured before user acted.
        after : ScreenObservation
            Observation captured after user acted.
        expected : dict
            Expected transition description. Supported keys:
                process_starts : str   — process name that must appear
                text_appears : str     — text that must be added
                target_disappears : str — target that must disappear
                screen_changed : bool  — any meaningful change occurred

        Returns
        -------
        ScreenVerificationResult
        """

        differ = ObservationDiffer()
        target = expected.get("target_disappears") or expected.get("text_appears")
        diff = differ.compare(before, after, target=target)

        # ----------------------------------------------------------
        # Process started
        # ----------------------------------------------------------
        process_starts = expected.get("process_starts")
        if process_starts:
            proc_lower = str(process_starts).lower()
            if proc_lower in diff.processes_started:
                return ScreenVerificationResult(
                    success=True,
                    message=f"Process '{process_starts}' started.",
                    verification_type="TRANSITION_VERIFIED",
                    metadata={"processes_started": diff.processes_started},
                )

        # ----------------------------------------------------------
        # Text appeared (was not present before)
        # ----------------------------------------------------------
        text_appears = expected.get("text_appears")
        if text_appears:
            text_lower = str(text_appears).strip().lower()
            for added in diff.added_text:
                if text_lower in added or added in text_lower:
                    return ScreenVerificationResult(
                        success=True,
                        message=(
                            f"Text '{text_appears}' appeared after action."
                        ),
                        verification_type="TRANSITION_VERIFIED",
                        metadata={"added_text": diff.added_text},
                    )

        # ----------------------------------------------------------
        # Target disappeared
        # ----------------------------------------------------------
        if expected.get("target_disappears") and diff.target_disappeared:
            return ScreenVerificationResult(
                success=True,
                message=(
                    f"Target '{target}' disappeared after action."
                ),
                verification_type="TRANSITION_VERIFIED",
            )

        # ----------------------------------------------------------
        # Generic meaningful screen change
        # ----------------------------------------------------------
        if expected.get("screen_changed") and diff.any_change:
            # Only accept if more than trivial noise.
            if (
                diff.process_change
                or diff.window_title_changed
                or len(diff.added_elements) >= 2
                or len(diff.added_text) >= 2
            ):
                return ScreenVerificationResult(
                    success=True,
                    message="Meaningful screen change detected.",
                    verification_type="TRANSITION_VERIFIED",
                    metadata={
                        "added_elements": len(diff.added_elements),
                        "added_text": len(diff.added_text),
                    },
                )

        return ScreenVerificationResult(
            success=False,
            message="Expected state transition not detected.",
            verification_type="TRANSITION_NOT_VERIFIED",
            metadata={
                "diff_any_change": diff.any_change,
                "processes_started": diff.processes_started,
                "added_text": diff.added_text,
            },
        )

    def verify_text_appeared(
        self,
        before,
        after,
        text: str,
    ) -> ScreenVerificationResult:
        """
        Verify that specific text was ADDED between two observations.

        CRITICAL: If the text was already present in the 'before'
        observation, this method returns False.  This prevents
        TYPE_TEXT false positives where the text existed before
        the instruction was given.

        Parameters
        ----------
        before : ScreenObservation
            Baseline observation captured before user acted.
        after : ScreenObservation
            Observation captured after user acted.
        text : str
            The text that should have been typed/added.

        Returns
        -------
        ScreenVerificationResult
        """

        if not text or not text.strip():
            return ScreenVerificationResult(
                success=False,
                message="Text cannot be empty.",
                verification_type="TEXT_APPEARED",
            )

        differ = ObservationDiffer()
        diff = differ.compare(before, after)

        text_lower = text.strip().lower()

        # Check whether the text was added (appears in diff.added_text).
        for added in diff.added_text:
            if text_lower in added or added in text_lower:
                return ScreenVerificationResult(
                    success=True,
                    message=(
                        f"Text '{text}' was added after the baseline."
                    ),
                    verification_type="TEXT_APPEARED",
                    metadata={"added_text": diff.added_text},
                )

        # Check whether the text was already present before.
        before_texts = differ._element_texts(before)
        was_already_there = any(
            text_lower in t or t in text_lower
            for t in before_texts
        )

        if was_already_there:
            return ScreenVerificationResult(
                success=False,
                message=(
                    f"Text '{text}' was already present before the action. "
                    "Cannot confirm user typed it."
                ),
                verification_type="TEXT_APPEARED",
            )

        return ScreenVerificationResult(
            success=False,
            message=f"Text '{text}' was not found after the action.",
            verification_type="TEXT_APPEARED",
        )