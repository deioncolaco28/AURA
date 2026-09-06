from app.perception.grounding import UIGrounder
from app.perception.ocr import TextElement


def test_find_text():
    elements = [
        TextElement(
            text="File",
            x=10,
            y=20,
            width=30,
            height=20,
            confidence=95.0,
        ),
        TextElement(
            text="Edit",
            x=50,
            y=20,
            width=30,
            height=20,
            confidence=94.0,
        ),
    ]

    grounder = UIGrounder()

    result = grounder.find_text(
        elements,
        "File",
    )

    assert result is not None
    assert result.text == "File"


def test_find_text_is_case_insensitive():
    elements = [
        TextElement(
            text="File",
            x=10,
            y=20,
            width=30,
            height=20,
            confidence=95.0,
        ),
    ]

    grounder = UIGrounder()

    result = grounder.find_text(
        elements,
        "file",
    )

    assert result is not None


def test_find_missing_text():
    elements = [
        TextElement(
            text="File",
            x=10,
            y=20,
            width=30,
            height=20,
            confidence=95.0,
        ),
    ]

    grounder = UIGrounder()

    result = grounder.find_text(
        elements,
        "Save",
    )

    assert result is None


def test_text_element_center():
    element = TextElement(
        text="File",
        x=10,
        y=20,
        width=30,
        height=20,
        confidence=95.0,
    )

    assert element.center == (25, 30)