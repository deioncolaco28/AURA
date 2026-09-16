from dataclasses import dataclass, field
from typing import Any

from PIL import ImageChops

from app.perception.grounding import UIGrounder
from app.perception.ocr import TesseractOCR
from app.perception.screenshot import ScreenshotCapture
from app.verification.verifier import (
    VerificationResult,
    Verifier,
)


@dataclass
class ScreenVerificationResult:
    success: bool
    message: str = ""
    verification_type: str | None = None
    metadata: dict[str, Any] = field(
        default_factory=dict
    )
    detected_text: list[str] = field(
        default_factory=list
    )

    def __bool__(self) -> bool:
        return self.success

    @property
    def passed(self) -> bool:
        return self.success


class ScreenVerifier(Verifier):
    """
    Verifies expected conditions against
    the current screen.
    """

    def __init__(
        self,
        screenshot_capture=None,
        ocr=None,
        grounder=None,
    ):
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

        self._previous_screenshot = None

    def verify(
        self,
        action,
    ) -> VerificationResult:

        verification = getattr(
            action,
            "verification",
            {},
        )

        if not isinstance(
            verification,
            dict,
        ):
            verification = {}

        verification_type = (
            verification.get("type")
        )

        if (
            verification_type
            == "SCREEN_CONTAINS_TEXT"
        ):
            text = verification.get(
                "text"
            )

            result = self.contains_text(
                text
            )

            return VerificationResult(
                success=result.success,
                message=result.message,
                verification_type=(
                    result.verification_type
                ),
                metadata={
                    **result.metadata,
                    "detected_text": (
                        result.detected_text
                    ),
                },
            )

        if (
            verification_type
            == "SCREEN_DOES_NOT_CONTAIN_TEXT"
        ):
            text = verification.get(
                "text"
            )

            result = (
                self.does_not_contain_text(
                    text
                )
            )

            return VerificationResult(
                success=result.success,
                message=result.message,
                verification_type=(
                    result.verification_type
                ),
                metadata={
                    **result.metadata,
                    "detected_text": (
                        result.detected_text
                    ),
                },
            )

        if (
            verification_type
            == "SCREEN_CHANGED"
        ):
            result = (
                self.has_screen_changed()
            )

            return VerificationResult(
                success=result.success,
                message=result.message,
                verification_type=(
                    result.verification_type
                ),
                metadata=result.metadata,
            )

        return VerificationResult(
            success=False,
            message=(
                "Unsupported screen "
                "verification type."
            ),
            verification_type=(
                verification_type
            ),
        )

    def contains_text(
        self,
        text: str,
    ) -> ScreenVerificationResult:

        if not text:
            return ScreenVerificationResult(
                success=False,
                message=(
                    "Could not find '' "
                    "on the screen."
                ),
                verification_type=(
                    "SCREEN_CONTAINS_TEXT"
                ),
                detected_text=[],
            )

        try:
            image = (
                self.screenshot_capture.capture()
            )

            elements = (
                self.ocr.detect_text(
                    image
                )
            )

            detected_text = [
                element.text
                for element in elements
                if getattr(
                    element,
                    "text",
                    None,
                )
            ]

            result = self.grounder.find_text(
                elements,
                text,
            )

            if result is not None:
                return ScreenVerificationResult(
                    success=True,
                    message=(
                        f"Found '{text}' "
                        "on the screen."
                    ),
                    verification_type=(
                        "SCREEN_CONTAINS_TEXT"
                    ),
                    detected_text=(
                        detected_text
                    ),
                )

            return ScreenVerificationResult(
                success=False,
                message=(
                    f"Could not find "
                    f"'{text}' on the screen."
                ),
                verification_type=(
                    "SCREEN_CONTAINS_TEXT"
                ),
                detected_text=(
                    detected_text
                ),
            )

        except Exception as error:
            return ScreenVerificationResult(
                success=False,
                message=str(error),
                verification_type=(
                    "SCREEN_CONTAINS_TEXT"
                ),
                detected_text=[],
            )

    def does_not_contain_text(
        self,
        text: str,
    ) -> ScreenVerificationResult:

        if not text:
            return ScreenVerificationResult(
                success=True,
                message=(
                    "Text is not present "
                    "on the screen."
                ),
                verification_type=(
                    "SCREEN_DOES_NOT_CONTAIN_TEXT"
                ),
                detected_text=[],
            )

        try:
            image = (
                self.screenshot_capture.capture()
            )

            elements = (
                self.ocr.detect_text(
                    image
                )
            )

            detected_text = [
                element.text
                for element in elements
                if getattr(
                    element,
                    "text",
                    None,
                )
            ]

            result = self.grounder.find_text(
                elements,
                text,
            )

            if result is None:
                return ScreenVerificationResult(
                    success=True,
                    message=(
                        f"Could not find "
                        f"'{text}' on the screen."
                    ),
                    verification_type=(
                        "SCREEN_DOES_NOT_CONTAIN_TEXT"
                    ),
                    detected_text=(
                        detected_text
                    ),
                )

            return ScreenVerificationResult(
                success=False,
                message=(
                    f"Found '{text}' "
                    "on the screen."
                ),
                verification_type=(
                    "SCREEN_DOES_NOT_CONTAIN_TEXT"
                ),
                detected_text=(
                    detected_text
                ),
            )

        except Exception as error:
            return ScreenVerificationResult(
                success=False,
                message=str(error),
                verification_type=(
                    "SCREEN_DOES_NOT_CONTAIN_TEXT"
                ),
                detected_text=[],
            )

    def has_screen_changed(
        self,
    ) -> ScreenVerificationResult:

        try:
            current = (
                self.screenshot_capture.capture()
            )

            if self._previous_screenshot is None:
                self._previous_screenshot = (
                    current
                )

                return ScreenVerificationResult(
                    success=True,
                    message=(
                        "Initial screen "
                        "captured."
                    ),
                    verification_type=(
                        "SCREEN_CHANGED"
                    ),
                )

            difference = ImageChops.difference(
                self._previous_screenshot,
                current,
            )

            changed = (
                difference.getbbox()
                is not None
            )

            self._previous_screenshot = (
                current
            )

            if changed:
                return ScreenVerificationResult(
                    success=True,
                    message=(
                        "Screen changed."
                    ),
                    verification_type=(
                        "SCREEN_CHANGED"
                    ),
                )

            return ScreenVerificationResult(
                success=False,
                message=(
                    "Screen did not change."
                ),
                verification_type=(
                    "SCREEN_CHANGED"
                ),
            )

        except Exception as error:
            return ScreenVerificationResult(
                success=False,
                message=str(error),
                verification_type=(
                    "SCREEN_CHANGED"
                ),
            )