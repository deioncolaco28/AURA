from abc import ABC, abstractmethod


class VerificationResult:
    """Represents the result of verifying an action."""

    def __init__(
        self,
        success: bool,
        message: str = "",
    ):
        self.success = success
        self.message = message

    def __bool__(self) -> bool:
        return self.success


class Verifier(ABC):
    """Interface for action verification."""

    @abstractmethod
    def verify(self, *args, **kwargs) -> VerificationResult:
        """Verify whether an action succeeded."""
        raise NotImplementedError