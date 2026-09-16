from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VerificationResult:
    """Represents the result of a verification operation."""

    success: bool

    message: str = ""

    verification_type: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __bool__(self) -> bool:
        """
        Allow VerificationResult to be used directly
        in boolean expressions.
        """

        return self.success

    @property
    def passed(self) -> bool:
        """Backward-compatible alias for success."""

        return self.success


class Verifier(ABC):
    """Abstract interface for verification components."""

    @abstractmethod
    def verify(
        self,
        action,
    ) -> VerificationResult:
        raise NotImplementedError