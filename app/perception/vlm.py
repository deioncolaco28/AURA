from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VLMElement:
    """Represents an element detected by a VLM."""

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
    """Result returned by a visual-language model."""

    elements: list[VLMElement] = field(
        default_factory=list
    )

    description: str = ""

    raw_response: Any = None


class VLM(ABC):
    """Abstract interface for visual-language models."""

    @abstractmethod
    def analyze(
        self,
        image,
        instruction: str | None = None,
    ) -> VLMResult:
        """Analyze a screenshot."""

        raise NotImplementedError


class MockVLM(VLM):
    """Development VLM used before a real model is connected."""

    def analyze(
        self,
        image,
        instruction: str | None = None,
    ) -> VLMResult:
        """Return an empty visual analysis."""

        return VLMResult(
            elements=[],
            description=(
                "No VLM model is configured."
            ),
        )