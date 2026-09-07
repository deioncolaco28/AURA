import json
from typing import Any

from app.perception.vlm import (
    VLM,
    VLMElement,
    VLMResult,
)


class VLMResponseParser:
    """
    Validates and converts raw structured VLM responses
    into AURA VLMResult objects.
    """

    REQUIRED_ELEMENT_FIELDS = (
        "element_type",
        "description",
        "x",
        "y",
        "width",
        "height",
    )

    def parse(
        self,
        response: Any,
    ) -> VLMResult:
        data = self._normalize_response(response)

        if not isinstance(data, dict):
            raise ValueError(
                "VLM response must be a JSON object."
            )

        raw_elements = data.get(
            "elements",
            [],
        )

        if not isinstance(raw_elements, list):
            raise ValueError(
                "VLM 'elements' must be a list."
            )

        elements = []

        for index, raw_element in enumerate(
            raw_elements
        ):
            elements.append(
                self._parse_element(
                    raw_element,
                    index,
                )
            )

        description = data.get(
            "screen_description",
            data.get("description", ""),
        )

        if description is None:
            description = ""

        return VLMResult(
            elements=elements,
            description=str(description),
            raw_response=response,
        )

    def _parse_element(
        self,
        data: Any,
        index: int,
    ) -> VLMElement:
        if not isinstance(data, dict):
            raise ValueError(
                f"VLM element {index} must be an object."
            )

        missing = [
            field
            for field in self.REQUIRED_ELEMENT_FIELDS
            if field not in data
        ]

        if missing:
            raise ValueError(
                f"VLM element {index} is missing fields: "
                f"{', '.join(missing)}"
            )

        element_type = str(
            data["element_type"]
        ).strip()

        description = str(
            data["description"]
        ).strip()

        if not element_type:
            raise ValueError(
                f"VLM element {index} has an empty "
                f"element_type."
            )

        if not description:
            raise ValueError(
                f"VLM element {index} has an empty "
                f"description."
            )

        x = self._coordinate(
            data["x"],
            "x",
            index,
        )

        y = self._coordinate(
            data["y"],
            "y",
            index,
        )

        width = self._dimension(
            data["width"],
            "width",
            index,
        )

        height = self._dimension(
            data["height"],
            "height",
            index,
        )

        confidence = self._confidence(
            data.get("confidence", 0.0)
        )

        text = data.get("text")

        if text is not None:
            text = str(text).strip() or None

        attributes = data.get(
            "attributes",
            {},
        )

        if not isinstance(attributes, dict):
            attributes = {}

        return VLMElement(
            element_type=element_type,
            description=description,
            x=x,
            y=y,
            width=width,
            height=height,
            confidence=confidence,
            text=text,
            attributes=attributes,
        )

    def _coordinate(
        self,
        value: Any,
        name: str,
        index: int,
    ) -> int:
        try:
            value = float(value)
        except (TypeError, ValueError):
            raise ValueError(
                f"VLM element {index} has invalid "
                f"{name} coordinate."
            )

        if value < 0:
            raise ValueError(
                f"VLM element {index} has negative "
                f"{name} coordinate."
            )

        return int(round(value))

    def _dimension(
        self,
        value: Any,
        name: str,
        index: int,
    ) -> int:
        try:
            value = float(value)
        except (TypeError, ValueError):
            raise ValueError(
                f"VLM element {index} has invalid "
                f"{name} dimension."
            )

        if value <= 0:
            raise ValueError(
                f"VLM element {index} has invalid "
                f"{name} dimension."
            )

        return int(round(value))

    def _confidence(
        self,
        value: Any,
    ) -> float:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            confidence = 0.0

        return max(
            0.0,
            min(1.0, confidence),
        )

    def _normalize_response(
        self,
        response: Any,
    ) -> Any:
        if isinstance(response, dict):
            return response

        if isinstance(response, str):
            try:
                return json.loads(response)
            except json.JSONDecodeError as error:
                raise ValueError(
                    "VLM response is not valid JSON."
                ) from error

        raise ValueError(
            "Unsupported VLM response type."
        )


class StructuredVLMAdapter(VLM):
    """
    Adapter for a VLM provider that returns structured JSON.

    The actual model/provider is intentionally injected through
    the analyze_callable so AURA does not depend on one provider.
    """

    def __init__(
        self,
        analyze_callable,
        parser: VLMResponseParser | None = None,
    ):
        self.analyze_callable = analyze_callable
        self.parser = (
            parser
            or VLMResponseParser()
        )

    def analyze(
        self,
        image,
        instruction: str | None = None,
    ) -> VLMResult:
        if self.analyze_callable is None:
            raise RuntimeError(
                "No VLM analyze callable is configured."
            )

        response = self.analyze_callable(
            image=image,
            instruction=instruction,
        )

        return self.parser.parse(response)