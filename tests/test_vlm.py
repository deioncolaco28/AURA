from PIL import Image
import pytest

from app.perception.grounding import UIGrounder
from app.perception.perception_manager import (
    PerceptionManager,
)
from app.perception.vlm import (
    MockVLM,
    VLMElement,
)
from app.perception.vlm_adapter import (
    StructuredVLMAdapter,
    VLMResponseParser,
)


def test_vlm_response_parser_parses_valid_response():
    parser = VLMResponseParser()

    response = {
        "screen_description": (
            "Windows search is open."
        ),
        "elements": [
            {
                "element_type": "search_result",
                "description": (
                    "Notepad application search result"
                ),
                "text": "Notepad",
                "x": 100,
                "y": 200,
                "width": 200,
                "height": 50,
                "confidence": 0.92,
            }
        ],
    }

    result = parser.parse(response)

    assert len(result.elements) == 1

    element = result.elements[0]

    assert element.text == "Notepad"
    assert element.description == (
        "Notepad application search result"
    )
    assert element.x == 100
    assert element.y == 200
    assert element.confidence == 0.92


def test_vlm_parser_rejects_missing_fields():
    parser = VLMResponseParser()

    response = {
        "elements": [
            {
                "element_type": "button",
                "description": "Search button",
            }
        ]
    }

    with pytest.raises(ValueError):
        parser.parse(response)


def test_vlm_parser_clamps_confidence():
    parser = VLMResponseParser()

    response = {
        "elements": [
            {
                "element_type": "button",
                "description": "Search button",
                "x": 10,
                "y": 20,
                "width": 100,
                "height": 40,
                "confidence": 5.0,
            }
        ]
    }

    result = parser.parse(response)

    assert result.elements[0].confidence == 1.0


def test_vlm_parser_accepts_json_string():
    parser = VLMResponseParser()

    response = """
    {
        "screen_description": "A test screen",
        "elements": [
            {
                "element_type": "button",
                "description": "Test button",
                "x": 10,
                "y": 20,
                "width": 100,
                "height": 40,
                "confidence": 0.8
            }
        ]
    }
    """

    result = parser.parse(response)

    assert result.description == "A test screen"
    assert len(result.elements) == 1


def test_mock_vlm_returns_configured_elements():
    element = VLMElement(
        element_type="button",
        description="Search button",
        x=10,
        y=20,
        width=100,
        height=40,
        confidence=0.9,
        text="Search",
    )

    vlm = MockVLM(
        elements=[element],
        description="Test screen",
    )

    image = Image.new(
        "RGB",
        (500, 500),
    )

    result = vlm.analyze(
        image,
        instruction="Find Search",
    )

    assert result.description == "Test screen"
    assert len(result.elements) == 1
    assert result.elements[0].text == "Search"


def test_perception_manager_preserves_vlm_description():
    element = VLMElement(
        element_type="button",
        description="Search button",
        x=10,
        y=20,
        width=100,
        height=40,
        confidence=0.9,
        text="Search",
    )

    vlm = MockVLM(
        elements=[element]
    )

    manager = PerceptionManager(
        vlm=vlm
    )

    image = Image.new(
        "RGB",
        (500, 500),
    )

    result = manager.analyze(
        image,
        instruction="Find Search",
    )

    assert len(result.elements) == 1

    assert result.elements[0].description == (
        "Search button"
    )

    assert result.elements[0].source == "VLM"


def test_grounder_uses_vlm_description():
    element = VLMElement(
        element_type="button",
        description="Magnifying glass search button",
        x=10,
        y=20,
        width=100,
        height=40,
        confidence=0.9,
    )

    vlm = MockVLM(
        elements=[element]
    )

    manager = PerceptionManager(
        vlm=vlm
    )

    image = Image.new(
        "RGB",
        (500, 500),
    )

    perception = manager.analyze(
        image
    )

    grounder = UIGrounder()

    result = grounder.ground(
        perception.elements,
        "search button",
    )

    assert result.found
    assert result.score >= 0.65


def test_structured_vlm_adapter():
    def fake_provider(
        image,
        instruction,
    ):
        return {
            "screen_description": (
                "Fake screen"
            ),
            "elements": [
                {
                    "element_type": "button",
                    "description": "Submit button",
                    "text": "Submit",
                    "x": 50,
                    "y": 60,
                    "width": 120,
                    "height": 40,
                    "confidence": 0.95,
                }
            ],
        }

    vlm = StructuredVLMAdapter(
        analyze_callable=fake_provider
    )

    image = Image.new(
        "RGB",
        (500, 500),
    )

    result = vlm.analyze(
        image,
        "Find Submit",
    )

    assert result.description == "Fake screen"
    assert len(result.elements) == 1
    assert result.elements[0].text == "Submit"