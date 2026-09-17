from app.perception.grounding import (
    UIGrounder,
)
from app.perception.ui_element import UIElement


def test_grounder_exact_match():

    grounder = UIGrounder()

    elements = [
        UIElement(
            element_id="1",
            element_type="button",
            text="Notepad",
            x=100,
            y=100,
            width=100,
            height=40,
        )
    ]

    result = grounder.ground(
        elements,
        "Notepad",
    )

    assert result.found
    assert result.element == elements[0]

    assert result.score >= 1.0

    assert "Exact" in result.reason


def test_grounder_case_insensitive_match():

    grounder = UIGrounder()

    element = UIElement(
        element_id="1",
        element_type="button",
        text="Notepad",
        x=100,
        y=100,
        width=100,
        height=40,
    )

    result = grounder.ground(
        [element],
        "notepad",
    )

    assert result.found
    assert result.element == element
    assert result.score >= 1.0


def test_grounder_description_match():

    grounder = UIGrounder()

    element = UIElement(
        element_id="1",
        element_type="button",
        description="Open Notepad application",
        x=100,
        y=100,
        width=100,
        height=40,
    )

    result = grounder.ground(
        [element],
        "Notepad",
    )

    assert result.found
    assert result.element == element

    assert result.score >= 0.75


def test_grounder_fused_element():

    grounder = UIGrounder()

    element = UIElement(
        element_id="fused-1",
        element_type="button",
        text="Notepad",
        description="Notepad application button",
        x=100,
        y=100,
        width=120,
        height=40,
        confidence=0.95,
        source="FUSED",
    )

    result = grounder.ground(
        [element],
        "Notepad",
    )

    assert result.found
    assert result.element == element

    assert result.score >= 1.0


def test_grounder_prefers_exact_match():

    grounder = UIGrounder()

    exact = UIElement(
        element_id="1",
        element_type="button",
        text="Notepad",
        x=100,
        y=100,
        width=100,
        height=40,
    )

    partial = UIElement(
        element_id="2",
        element_type="button",
        text="Notepad application",
        x=300,
        y=100,
        width=150,
        height=40,
    )

    result = grounder.ground(
        [partial, exact],
        "Notepad",
    )

    assert result.found
    assert result.element == exact


def test_grounder_empty_target():

    grounder = UIGrounder()

    element = UIElement(
        element_id="1",
        element_type="button",
        text="Notepad",
    )

    result = grounder.ground(
        [element],
        "",
    )

    assert not result.found
    assert result.score == 0.0


def test_grounder_missing_target():

    grounder = UIGrounder()

    element = UIElement(
        element_id="1",
        element_type="button",
        text="Notepad",
    )

    result = grounder.ground(
        [element],
        "Calculator",
    )

    assert not result.found
    assert result.score == 0.0


def test_grounder_find_text_returns_element():

    grounder = UIGrounder()

    element = UIElement(
        element_id="1",
        element_type="button",
        text="Notepad",
    )

    result = grounder.find_text(
        [element],
        "Notepad",
    )

    assert result.found is True
    assert result.element == element
    assert result.score >= 0.65
    assert result.reason == "Exact text match."