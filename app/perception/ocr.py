from abc import ABC, abstractmethod

import pytesseract


class OCR(ABC):
    """Interface for optical character recognition."""

    @abstractmethod
    def extract_text(self, image) -> str:
        """Extract text from an image."""
        raise NotImplementedError


class TesseractOCR(OCR):
    """OCR implementation using Tesseract."""

    def extract_text(self, image) -> str:
        """Extract visible text from an image."""

        return pytesseract.image_to_string(image)