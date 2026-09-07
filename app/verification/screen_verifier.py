from dataclasses import dataclass

from PIL import Image, ImageChops, ImageStat

from app.perception.grounding import UIGrounder
from app.perception.ocr import OCR
from app.perception.screenshot import ScreenshotCapture


@dataclass
class ScreenVerificationResult:
    """Result of a screen-state verification."""

    success: bool
    message: str
    detected_text: list[str]


class ScreenVerifier:
    """Verifies screen states using screenshots and OCR."""

    def __init__(
        self,
        screenshot_capture: ScreenshotCapture | None = None,
        ocr: OCR | None = None,
        grounder: UIGrounder | None = None,
    ):
        self.screenshot_capture = (
            screenshot_capture
            or ScreenshotCapture()
        )

        self.ocr = ocr

        self.grounder = (
            grounder
            or UIGrounder()
        )

    def capture_screen(self):
        """Capture the current screen."""

        return self.screenshot_capture.capture()

    def contains_text(
        self,
        target: str,
    ) -> ScreenVerificationResult:
        """Verify that target text is visible."""

        if not target.strip():
            return ScreenVerificationResult(
                success=False,
                message="Target text is empty.",
                detected_text=[],
            )

        if self.ocr is None:
            return ScreenVerificationResult(
                success=False,
                message="OCR is unavailable.",
                detected_text=[],
            )

        image = self.screenshot_capture.capture()

        elements = self.ocr.detect_text(
            image
        )

        detected_text = [
            element.text
            for element in elements
        ]

        element = self.grounder.find_text(
            elements,
            target,
        )

        if element is not None:
            return ScreenVerificationResult(
                success=True,
                message=(
                    f"Found '{target}' "
                    "on the screen."
                ),
                detected_text=detected_text,
            )

        return ScreenVerificationResult(
            success=False,
            message=(
                f"Could not find '{target}' "
                "on the screen."
            ),
            detected_text=detected_text,
        )

    def does_not_contain_text(
        self,
        target: str,
    ) -> ScreenVerificationResult:
        """Verify that target text is not visible."""

        result = self.contains_text(
            target
        )

        return ScreenVerificationResult(
            success=not result.success,
            message=(
                f"'{target}' is no longer visible."
                if not result.success
                else f"'{target}' is still visible."
            ),
            detected_text=result.detected_text,
        )

    def has_screen_changed(
        self,
        before,
        after,
        threshold: float = 3.0,
    ) -> bool:
        """Determine whether two screenshots differ."""

        if before is None or after is None:
            return False

        if not isinstance(
            before,
            Image.Image,
        ):
            return False

        if not isinstance(
            after,
            Image.Image,
        ):
            return False

        if before.size != after.size:
            return True

        before_small = before.resize(
            (160, 90)
        ).convert("RGB")

        after_small = after.resize(
            (160, 90)
        ).convert("RGB")

        difference = ImageChops.difference(
            before_small,
            after_small,
        )

        statistics = ImageStat.Stat(
            difference
        )

        mean_difference = sum(
            statistics.mean
        ) / len(statistics.mean)

        return mean_difference >= threshold