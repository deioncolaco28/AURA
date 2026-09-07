from app.perception.grounding import UIGrounder
from app.perception.ocr import OCR
from app.perception.screenshot import ScreenshotCapture
from app.tutoring.instruction import TutoringInstruction
from app.tutoring.overlay import HighlightOverlay
from app.voice.voice_manager import VoiceManager


class TutoringEngine:
    """Coordinates perception, highlighting, and voice guidance."""

    def __init__(
        self,
        voice_manager: VoiceManager,
        screenshot_capture: ScreenshotCapture | None = None,
        ocr: OCR | None = None,
        grounder: UIGrounder | None = None,
        overlay: HighlightOverlay | None = None,
    ):
        self.voice_manager = voice_manager

        self.screenshot_capture = (
            screenshot_capture or ScreenshotCapture()
        )

        self.ocr = ocr

        self.grounder = (
            grounder or UIGrounder()
        )

        self.overlay = (
            overlay or HighlightOverlay()
        )

    def guide(
        self,
        instruction: TutoringInstruction,
    ) -> None:
        """Provide one tutoring instruction."""

        self.voice_manager.speak(
            instruction.message
        )

        if (
            instruction.target
            and self.ocr is not None
        ):
            self._highlight_target(
                instruction.target
            )

    def _highlight_target(
        self,
        target: str,
    ) -> None:
        """Find and highlight a target on the screen."""

        image = self.screenshot_capture.capture()

        elements = self.ocr.detect_text(image)

        element = self.grounder.find_text(
            elements,
            target,
        )

        if element is None:
            self.voice_manager.speak(
                f"I could not find {target} on the screen."
            )
            return

        self.overlay.show(
            x=element.x,
            y=element.y,
            width=element.width,
            height=element.height,
        )