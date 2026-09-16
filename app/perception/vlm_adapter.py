import json
from typing import Any, Callable

from app.perception.vlm import VLM, VLMElement, VLMResult


class VLMResponseParser:
    REQUIRED_FIELDS = {
        "element_type",
        "description",
        "x",
        "y",
        "width",
        "height",
        "confidence",
    }

    def parse(self, response: dict[str, Any] | str) -> VLMResult:
        if isinstance(response, str):
            try:
                response = json.loads(response)
            except json.JSONDecodeError as error:
                raise ValueError("VLM response is not valid JSON.") from error

        if not isinstance(response, dict):
            raise TypeError("VLM response must be a dictionary or JSON string.")

        raw_elements = response.get("elements")

        if not isinstance(raw_elements, list):
            raise ValueError(
                "VLM response must contain an 'elements' list."
            )

        elements: list[VLMElement] = []

        for index, raw_element in enumerate(raw_elements):
            if not isinstance(raw_element, dict):
                raise ValueError(
                    f"VLM element {index} must be an object."
                )

            missing = self.REQUIRED_FIELDS - set(raw_element.keys())

            if missing:
                raise ValueError(
                    f"VLM element {index} is missing required fields: "
                    f"{sorted(missing)}"
                )

            try:
                x = int(raw_element["x"])
                y = int(raw_element["y"])
                width = int(raw_element["width"])
                height = int(raw_element["height"])
                confidence = float(raw_element["confidence"])
            except (TypeError, ValueError, KeyError) as error:
                raise ValueError(
                    f"Invalid VLM element {index}: {raw_element}"
                ) from error

            confidence = max(0.0, min(1.0, confidence))

            attributes = raw_element.get("attributes", {})

            if not isinstance(attributes, dict):
                attributes = {}

            elements.append(
                VLMElement(
                    element_type=str(raw_element["element_type"]),
                    description=str(raw_element["description"]),
                    text=str(raw_element.get("text", "")),
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                    confidence=confidence,
                    element_id=str(
                        raw_element.get(
                            "element_id",
                            f"vlm-{index}",
                        )
                    ),
                    attributes=attributes,
                )
            )

        description = response.get(
            "description",
            response.get("screen_description", ""),
        )

        try:
            overall_confidence = float(
                response.get("confidence", 0.0)
            )
        except (TypeError, ValueError):
            overall_confidence = 0.0

        metadata = response.get("metadata", {})

        if not isinstance(metadata, dict):
            metadata = {}

        return VLMResult(
            elements=elements,
            description=str(description),
            model_name=str(response.get("model_name", "")),
            confidence=overall_confidence,
            metadata=metadata,
        )


class StructuredVLMAdapter(VLM):
    """
    Adapter for VLM providers that return structured JSON-compatible data.

    The callable receives:
        image
        instruction

    and must return either:
        dict
        or
        JSON string
    """

    def __init__(
        self,
        analyze_callable: Callable | None = None,
        parser: VLMResponseParser | None = None,
    ):
        self.analyze_callable = analyze_callable
        self.parser = parser or VLMResponseParser()

    def analyze(
        self,
        image,
        instruction: str | None = None,
    ) -> VLMResult:

        if self.analyze_callable is None:
            return VLMResult(
                elements=[],
                description="",
                model_name="structured-adapter",
            )

        response = self.analyze_callable(
            image,
            instruction,
        )

        return self.parser.parse(response)


class ProviderVLM(VLM):
    """
    Production-facing VLM adapter.

    AURA does not depend on a specific VLM vendor or SDK.

    The provider callable is responsible only for communicating
    with the selected vision model.

    AURA remains responsible for:
        provider response parsing
        validation
        grounding
        action selection
    """

    def __init__(
        self,
        provider: Callable,
        model_name: str = "external-vlm",
        parser: VLMResponseParser | None = None,
    ):
        if not callable(provider):
            raise TypeError(
                "VLM provider must be callable."
            )

        self.provider = provider
        self.model_name = model_name
        self.parser = parser or VLMResponseParser()

    def analyze(
        self,
        image,
        instruction: str | None = None,
    ) -> VLMResult:

        response = self.provider(
            image=image,
            instruction=instruction,
        )

        result = self.parser.parse(response)

        if not result.model_name:
            result.model_name = self.model_name

        result.metadata.setdefault(
            "provider",
            self.model_name,
        )

        result.metadata.setdefault(
            "instruction",
            instruction,
        )

        return result