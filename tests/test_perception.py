from unittest.mock import Mock, patch

from app.perception.ocr import TextElement, TesseractOCR


def test_text_element_center():
    element = TextElement(
        text="Notepad",
        x=100,
        y=200,
        width=120,
        height=40,
        confidence=95.0,
    )

    assert element.center == (
        160,
        220,
    )


def test_tesseract_extract_text():
    ocr = TesseractOCR()

    image = Mock()

    with patch(
        "app.perception.ocr.pytesseract.image_to_string"
    ) as mock_ocr:
        mock_ocr.return_value = "Notepad"

        result = ocr.extract_text(
            image
        )

    assert result == "Notepad"


def test_tesseract_detect_text():
    ocr = TesseractOCR()

    image = Mock()

    with patch(
        "app.perception.ocr.pytesseract.image_to_data"
    ) as mock_ocr:
        mock_ocr.return_value = {
            "text": [
                "Notepad",
                "",
            ],
            "conf": [
                "95.0",
                "-1",
            ],
            "left": [
                "100",
                "0",
            ],
            "top": [
                "200",
                "0",
            ],
            "width": [
                "120",
                "0",
            ],
            "height": [
                "40",
                "0",
            ],
        }

        elements = ocr.detect_text(
            image
        )

    assert len(elements) == 1
    assert elements[0].text == "Notepad"
    assert elements[0].confidence == 95.0