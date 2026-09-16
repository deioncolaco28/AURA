from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VLMElement:
    """
    Represents a UI element detected by a Vision-Language Model.
    """

    element_type: str
    description: str = ""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    confidence: float = 0.0
    text: str = ""
    element_id: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.confidence = max(
            0.0,
            min(1.0, float(self.confidence)),
        )

    @property
    def center(self) -> tuple[int, int]:
        return (
            self.x + self.width // 2,
            self.y + self.height // 2,
        )

    @property
    def bounds(self) -> tuple[int, int, int, int]:
        return (
            self.x,
            self.y,
            self.width,
            self.height,
        )


@dataclass
class VLMResult:
    """
    Result returned by a Vision-Language Model.
    """

    elements: list[VLMElement] = field(default_factory=list)

    # Existing AURA API
    description: str = ""

    # Optional model metadata
    model_name: str = ""
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.confidence = max(
            0.0,
            min(1.0, float(self.confidence)),
        )

    @property
    def screen_description(self) -> str:
        """
        Compatibility alias for newer code.
        """
        return self.description

    @property
    def element_count(self) -> int:
        return len(self.elements)

    @property
    def has_elements(self) -> bool:
        return bool(self.elements)


class VLM(ABC):
    """
    Abstract interface for Vision-Language Model perception.
    """

    @abstractmethod
    def analyze(
        self,
        image,
        instruction: str | None = None,
    ) -> VLMResult:
        raise NotImplementedError


class MockVLM(VLM):
    """
    Deterministic VLM implementation used for testing and development.
    """

    def __init__(
        self,
        elements: list[VLMElement] | None = None,
        description: str = "",
        model_name: str = "mock-vlm",
    ):
        self.elements = elements or []
        self.description = description
        self.model_name = model_name

    def analyze(
        self,
        image,
        instruction: str | None = None,
    ) -> VLMResult:

        elements = list(self.elements)

        if instruction:
            instruction_lower = instruction.strip().lower()

            # Support instructions such as:
            # "Find Search"
            # "Find Submit button"
            #
            # The word "find" is an instruction rather than part
            # of the actual target.
            target = instruction_lower

            if target.startswith("find "):
                target = target[5:].strip()

            if target:
                elements = [
                    element
                    for element in elements
                    if (
                        target in element.text.lower()
                        or target in element.description.lower()
                        or target in element.element_type.lower()
                    )
                ]

        average_confidence = (
            sum(
                element.confidence
                for element in elements
            )
            / len(elements)
            if elements
            else 0.0
        )

        return VLMResult(
            elements=elements,
            description=self.description,
            model_name=self.model_name,
            confidence=average_confidence,
        )