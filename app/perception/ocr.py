from abc import ABC, abstractmethod
from dataclasses import dataclass

import pytesseract
from pytesseract import Output


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
        """Return the center coordinate of the text."""

        return (
            self.x + self.width // 2,
            self.y + self.height // 2,
        )


class OCR(ABC):
    """Interface for optical character recognition."""

    @abstractmethod
    def extract_text(self, image) -> str:
        """Extract text from an image."""
        raise NotImplementedError

    @abstractmethod
    def detect_text(self, image) -> list[TextElement]:
        """Detect text and its screen position."""
        raise NotImplementedError


class TesseractOCR(OCR):
    """OCR implementation using Tesseract."""

    def extract_text(self, image) -> str:
        """Extract visible text from an image."""

        return pytesseract.image_to_string(image)

    def detect_text(self, image) -> list[TextElement]:
        """Detect text and its bounding boxes."""

        data = pytesseract.image_to_data(
            image,
            output_type=Output.DICT,
        )

        elements = []

        for i, text in enumerate(data["text"]):
            text = text.strip()

            if not text:
                continue

            try:
                confidence = float(data["conf"][i])
            except (ValueError, TypeError):
                confidence = 0.0

            if confidence < 0:
                continue

            elements.append(
                TextElement(
                    text=text,
                    x=int(data["left"][i]),
                    y=int(data["top"][i]),
                    width=int(data["width"][i]),
                    height=int(data["height"][i]),
                    confidence=confidence,
                )
            )

        return elements