from unittest.mock import Mock

from app.perception.ocr import TextElement
from app.perception.perception_manager import (
    PerceptionManager,
)
from app.perception.ui_element import UIElement
from app.perception.vlm import (
    MockVLM,
    VLMElement,
)


def test_perception_manager_uses_ocr():

    ocr = Mock()

    ocr.detect_text.return_value = [
        TextElement(
            text="Notepad",
            x=100,
            y=100,
            width=120,
            height=30,
            confidence=0.95,
        )
    ]

    manager = PerceptionManager(
        ocr=ocr
    )

    result = manager.analyze(
        image="test-image"
    )

    assert result.element_count == 1

    assert result.elements[0].text == "Notepad"

    assert result.elements[0].source == "OCR"

    assert "OCR" in result.sources_used


def test_perception_manager_uses_vlm():

    vlm = MockVLM(
        elements=[
            VLMElement(
                element_type="button",
                description="Notepad button",
                text="Notepad",
                x=100,
                y=100,
                width=120,
                height=30,
                confidence=0.90,
            )
        ],
        description="Windows search results",
    )

    manager = PerceptionManager(
        vlm=vlm
    )

    result = manager.analyze(
        image="test-image",
        instruction="Find Notepad",
    )

    assert result.element_count == 1

    element = result.elements[0]

    assert element.text == "Notepad"
    assert element.element_type == "button"
    assert element.source == "VLM"

    assert result.screen_description == (
        "Windows search results"
    )

    assert "VLM" in result.sources_used


def test_perception_manager_fuses_duplicate_ocr_vlm_elements():

    ocr = Mock()

    ocr.detect_text.return_value = [
        TextElement(
            text="Notepad",
            x=100,
            y=100,
            width=120,
            height=30,
            confidence=0.95,
        )
    ]

    vlm = MockVLM(
        elements=[
            VLMElement(
                element_type="button",
                description="Notepad button",
                text="Notepad",
                x=105,
                y=102,
                width=118,
                height=32,
                confidence=0.90,
            )
        ]
    )

    manager = PerceptionManager(
        ocr=ocr,
        vlm=vlm,
    )

    result = manager.analyze(
        image="test-image"
    )

    assert result.element_count == 1

    element = result.elements[0]

    assert element.source == "FUSED"

    assert element.text == "Notepad"

    assert element.description == "Notepad button"

    assert element.element_type == "button"

    assert set(
        element.attributes["fused_sources"]
    ) == {
        "OCR",
        "VLM",
    }

    assert (
        result.metadata["raw_element_count"]
        == 2
    )

    assert (
        result.metadata["fused_element_count"]
        == 1
    )

    assert (
        result.metadata["fusion_applied"]
        is True
    )


def test_perception_manager_keeps_distinct_elements():

    ocr = Mock()

    ocr.detect_text.return_value = [
        TextElement(
            text="Notepad",
            x=100,
            y=100,
            width=100,
            height=30,
            confidence=0.95,
        ),
        TextElement(
            text="Calculator",
            x=100,
            y=180,
            width=120,
            height=30,
            confidence=0.95,
        ),
    ]

    manager = PerceptionManager(
        ocr=ocr
    )

    result = manager.analyze(
        image="test-image"
    )

    assert result.element_count == 2

    assert result.elements[0].text == "Notepad"
    assert result.elements[1].text == "Calculator"


def test_perception_result_contains_text():

    ocr = Mock()

    ocr.detect_text.return_value = [
        TextElement(
            text="Notepad",
            x=100,
            y=100,
            width=100,
            height=30,
            confidence=0.95,
        )
    ]

    manager = PerceptionManager(
        ocr=ocr
    )

    result = manager.analyze(
        image="test-image"
    )

    assert result.contains_text(
        "Notepad"
    )

    assert result.contains_text(
        "notepad"
    )

    assert not result.contains_text(
        "Calculator"
    )


def test_perception_result_source_filtering():

    ocr = Mock()

    ocr.detect_text.return_value = [
        TextElement(
            text="Notepad",
            x=100,
            y=100,
            width=100,
            height=30,
            confidence=0.95,
        )
    ]

    vlm = MockVLM(
        elements=[
            VLMElement(
                element_type="button",
                description="Calculator button",
                text="Calculator",
                x=100,
                y=180,
                width=120,
                height=30,
                confidence=0.90,
            )
        ]
    )

    manager = PerceptionManager(
        ocr=ocr,
        vlm=vlm,
    )

    result = manager.analyze(
        image="test-image"
    )

    ocr_elements = (
        result.get_elements_by_source(
            "OCR"
        )
    )

    vlm_elements = (
        result.get_elements_by_source(
            "VLM"
        )
    )

    assert len(ocr_elements) == 1
    assert len(vlm_elements) == 1

    assert ocr_elements[0].text == "Notepad"
    assert vlm_elements[0].text == "Calculator"