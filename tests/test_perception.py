from unittest.mock import patch

from app.perception.screenshot import ScreenshotCapture
from app.perception.ocr import TesseractOCR


def test_screenshot_capture():
    capture = ScreenshotCapture()

    with patch(
        "app.perception.screenshot.pyautogui.screenshot"
    ) as mock_screenshot:

        mock_screenshot.return_value = "fake_image"

        image = capture.capture()

        assert image == "fake_image"

        mock_screenshot.assert_called_once()


def test_ocr_extract_text():
    ocr = TesseractOCR()

    with patch(
        "app.perception.ocr.pytesseract.image_to_string"
    ) as mock_ocr:

        mock_ocr.return_value = "Open File Edit"

        result = ocr.extract_text("fake_image")

        assert result == "Open File Edit"

        mock_ocr.assert_called_once_with("fake_image")