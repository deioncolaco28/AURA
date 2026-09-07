from abc import ABC, abstractmethod
from dataclasses import dataclass

import pytesseract


@dataclass
class TextElement:
    """Represents text detected on the screen."""

    text: str
    x: int
    y: int
    width: int
    height: int
    confidence: float

    @property
    def center(self) -> tuple[int, int]:
        """Return the center coordinates."""

        return (
            self.x + self.width // 2,
            self.y + self.height // 2,
        )


class OCR(ABC):
    """Abstract OCR interface."""

    @abstractmethod
    def extract_text(self, image) -> str:
        """Extract plain text from an image."""
        raise NotImplementedError

    @abstractmethod
    def detect_text(
        self,
        image,
    ) -> list[TextElement]:
        """Detect text elements and their positions."""
        raise NotImplementedError


class TesseractOCR(OCR):
    """Tesseract-based OCR implementation."""

    def __init__(
        self,
        language: str = "eng",
        minimum_confidence: float = 30.0,
    ):
        self.language = language
        self.minimum_confidence = (
            minimum_confidence
        )

    def extract_text(
        self,
        image,
    ) -> str:
        """Extract text from an image."""

        return pytesseract.image_to_string(
            image,
            lang=self.language,
        )

    def detect_text(
        self,
        image,
    ) -> list[TextElement]:
        """Detect text with coordinates."""

        data = pytesseract.image_to_data(
            image,
            lang=self.language,
            output_type=(
                pytesseract.Output.DICT
            ),
        )

        elements = []

        for index, text in enumerate(
            data["text"]
        ):
            text = text.strip()

            if not text:
                continue

            try:
                confidence = float(
                    data["conf"][index]
                )
            except (
                ValueError,
                TypeError,
            ):
                continue

            if confidence < self.minimum_confidence:
                continue

            elements.append(
                TextElement(
                    text=text,
                    x=int(data["left"][index]),
                    y=int(data["top"][index]),
                    width=int(
                        data["width"][index]
                    ),
                    height=int(
                        data["height"][index]
                    ),
                    confidence=confidence,
                )
            )

        return elements