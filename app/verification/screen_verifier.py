from dataclasses import dataclass, field
from typing import Any

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