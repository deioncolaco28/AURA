from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VLMElement:
    """Represents one element detected by a VLM."""

    element_type: str
    description: str

    x: int
    y: int
    width: int
    height: int

    confidence: float = 0.0
    text: str | None = None

    attributes: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class VLMResult:
    """Structured result returned by a VLM."""

    elements: list[VLMElement] = field(
        default_factory=list
    )

    description: str = ""

    raw_response: Any = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


class VLM(ABC):
    """Abstract interface for visual-language models."""

    @abstractmethod
    def analyze(
        self,
        image,
        instruction: str | None = None,
    ) -> VLMResult:
        raise NotImplementedError


class MockVLM(VLM):
    """
    Development VLM implementation.

    This allows the rest of AURA to be developed and tested
    before connecting a real visual-language model.
    """

    def __init__(
        self,
        elements: list[VLMElement] | None = None,
        description: str = "",
    ):
        self.elements = elements or []
        self.description = description

    def analyze(
        self,
        image,
        instruction: str | None = None,
    ) -> VLMResult:
        return VLMResult(
            elements=list(self.elements),
            description=self.description,
            metadata={
                "provider": "mock",
                "instruction": instruction,
            },
        )