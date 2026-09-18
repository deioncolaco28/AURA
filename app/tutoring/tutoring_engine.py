from app.perception.grounding import UIGrounder
from app.perception.ocr import OCR, TesseractOCR
from app.perception.screenshot import ScreenshotCapture
from app.tutoring.instruction import TutoringInstruction
from app.tutoring.overlay import HighlightOverlay
from app.voice.voice_manager import VoiceManager


class TutoringEngine:
    """
    Provides lower-level tutoring perception services.

    The TutoringController owns the tutoring workflow and speech.

    This engine is responsible for:
        - capturing the screen
        - detecting visible targets
        - grounding targets
        - highlighting targets

    It never:
        - speaks
        - clicks
        - types
        - presses keys
        - performs the user's requested action
    """

    def __init__(
        self,
        voice_manager: VoiceManager | None = None,
        screenshot_capture: ScreenshotCapture | None = None,
        ocr: OCR | None = None,
        grounder: UIGrounder | None = None,
        overlay: HighlightOverlay | None = None,
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

        self.overlay = (
            overlay
            or HighlightOverlay()
        )

    def guide(
        self,
        instruction: TutoringInstruction,
    ) -> bool:
        """
        Compatibility method for older callers.

        Speech is intentionally NOT performed here.

        The controller is the single owner of tutoring speech.

        Returns True when the target can be highlighted,
        or True for instructions without a target.
        """

        if instruction.target:
            return self.highlight_target(
                instruction.target
            )

        return True

    def highlight_target(
        self,
        target: str,
    ) -> bool:
        """
        Locate and highlight a visible UI target.

        Returns True when a sufficiently reliable
        target was found.

        This method only points to the target.
        It never interacts with it.
        """

        if not target or not target.strip():
            return False

        try:
            image = (
                self.screenshot_capture.capture()
            )

            elements = self.ocr.detect_text(
                image
            )

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

            self.overlay.show(
                x=element.x,
                y=element.y,
                width=element.width,
                height=element.height,
            )

            return True

        except Exception as error:
            print(
                f"Tutoring target detection error: "
                f"{error}"
            )
            return False

    def clear_highlight(self) -> None:
        """Remove the current tutoring highlight."""

        self.overlay.close()