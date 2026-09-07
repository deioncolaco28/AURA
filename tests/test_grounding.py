from app.perception.grounding import UIGrounder
from app.perception.ocr import TextElement


def test_grounder_finds_exact_text():
    grounder = UIGrounder()

    elements = [
        TextElement(
            text="Notepad",
            x=100,
            y=200,
            width=120,
            height=40,
            confidence=95.0,
        )
    ]

    result = grounder.ground(
        elements,
        "Notepad",
    )

    assert result.found is True
    assert result.element.text == "Notepad"
    assert result.score == 1.0


def test_grounder_finds_contained_text():
    grounder = UIGrounder()

    elements = [
        TextElement(
            text="Open Notepad",
            x=100,
            y=200,
            width=150,
            height=40,
            confidence=95.0,
        )
    ]

    result = grounder.ground(
        elements,
        "Notepad",
    )

    assert result.found is True
    assert result.element.text == "Open Notepad"
    assert result.score == 0.85


def test_grounder_returns_none_for_unknown_target():
    grounder = UIGrounder()

    elements = [
        TextElement(
            text="Calculator",
            x=100,
            y=200,
            width=150,
            height=40,
            confidence=95.0,
        )
    ]

    result = grounder.ground(
        elements,
        "Notepad",
    )

    assert result.found is False
    assert result.element is None


def test_grounder_normalizes_whitespace_and_case():
    grounder = UIGrounder()

    elements = [
        TextElement(
            text="  NOTEPAD  ",
            x=100,
            y=200,
            width=150,
            height=40,
            confidence=95.0,
        )
    ]

    result = grounder.ground(
        elements,
        "notepad",
    )

    assert result.found is True
    assert result.score == 1.0