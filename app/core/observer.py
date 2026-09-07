from abc import ABC, abstractmethod

from app.core.observation import ScreenObservation
from app.perception.ocr import TesseractOCR
from app.perception.perception_manager import (
    PerceptionManager,
)
from app.perception.screenshot import ScreenshotCapture


class ComputerObserver(ABC):
    """
    Abstract interface for observing the current
    computer state.
    """

    @abstractmethod
    def observe(self) -> ScreenObservation:
        raise NotImplementedError


class ScreenObserver(ComputerObserver):
    """
    Development implementation of ComputerObserver.

    Captures the current screen and analyzes it using
    the configured perception pipeline.
    """

    def __init__(
        self,
        screenshot_capture: ScreenshotCapture | None = None,
        perception_manager: PerceptionManager | None = None,
    ):
        self.screenshot_capture = (
            screenshot_capture
            or ScreenshotCapture()
        )

        self.perception_manager = (
            perception_manager
            or PerceptionManager(
                ocr=TesseractOCR()
            )
        )

    def observe(self) -> ScreenObservation:
        """
        Capture and analyze the current screen.
        """

        screenshot = (
            self.screenshot_capture.capture()
        )

        perception = (
            self.perception_manager.analyze(
                screenshot
            )
        )

        screen_text = self._extract_screen_text(
            perception
        )

        return ScreenObservation(
            screen_text=screen_text,
            elements=list(
                perception.elements
            ),
            screenshot=screenshot,
            metadata={
                "sources_used": (
                    perception.sources_used
                ),
                "screen_description": (
                    perception.screen_description
                ),
            },
        )

    @staticmethod
    def _extract_screen_text(
        perception,
    ) -> str:
        """
        Combine readable text from perceived UI elements.
        """

        texts = []

        for element in perception.elements:
            if element.text:
                texts.append(
                    element.text.strip()
                )

        return "\n".join(
            text
            for text in texts
            if text
        )