from unittest.mock import Mock

from app.perception.ocr import TextElement
from app.verification.screen_verifier import (
    ScreenVerifier,
)


def test_screen_verifier_finds_text():
    screenshot_capture = Mock()
    screenshot_capture.capture.return_value = Mock()

    ocr = Mock()
    ocr.detect_text.return_value = [
        TextElement(
            text="Notepad",
            x=100,
            y=200,
            width=120,
            height=40,
            confidence=95.0,
        )
    ]

    verifier = ScreenVerifier(
        screenshot_capture=screenshot_capture,
        ocr=ocr,
    )

    result = verifier.contains_text(
        "Notepad"
    )

    assert result.success is True
    assert (
        result.message
        == "Found 'Notepad' on the screen."
    )
    assert result.detected_text == [
        "Notepad"
    ]


def test_screen_verifier_does_not_find_text():
    screenshot_capture = Mock()
    screenshot_capture.capture.return_value = Mock()

    ocr = Mock()
    ocr.detect_text.return_value = [
        TextElement(
            text="Calculator",
            x=100,
            y=200,
            width=120,
            height=40,
            confidence=95.0,
        )
    ]

    verifier = ScreenVerifier(
        screenshot_capture=screenshot_capture,
        ocr=ocr,
    )

    result = verifier.contains_text(
        "Notepad"
    )

    assert result.success is False
    assert (
        result.message
        == "Could not find 'Notepad' on the screen."
    )


def test_screen_verifier_detects_missing_text():
    screenshot_capture = Mock()
    screenshot_capture.capture.return_value = Mock()

    ocr = Mock()
    ocr.detect_text.return_value = [
        TextElement(
            text="Calculator",
            x=100,
            y=200,
            width=120,
            height=40,
            confidence=95.0,
        )
    ]

    verifier = ScreenVerifier(
        screenshot_capture=screenshot_capture,
        ocr=ocr,
    )

    result = verifier.does_not_contain_text(
        "Notepad"
    )

    assert result.success is True