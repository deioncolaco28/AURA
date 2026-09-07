from dataclasses import dataclass, field
from typing import Any

from app.intelligence.action import Action


class FailureType:
    """Categories of failures during task execution."""

    EXECUTION = "EXECUTION_FAILURE"
    VERIFICATION = "VERIFICATION_FAILURE"
    UNKNOWN = "UNKNOWN_FAILURE"


@dataclass
class FailureInfo:
    """
    Structured information describing why an action failed.
    """

    action: Action

    error: str | None = None

    verification: dict[str, Any] = field(
        default_factory=dict
    )

    attempt: int = 0

    failure_type: str = FailureType.UNKNOWN

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    @property
    def has_error(self) -> bool:
        """Return True when an execution error exists."""

        return bool(
            self.error
            and self.error.strip()
        )

    @property
    def verification_type(self) -> str | None:
        """Return the configured verification type."""

        value = self.verification.get(
            "type"
        )

        if value is None:
            return None

        return str(value)

    @property
    def is_execution_failure(self) -> bool:
        """Return True when execution itself failed."""

        return (
            self.failure_type
            == FailureType.EXECUTION
        )

    @property
    def is_verification_failure(self) -> bool:
        """Return True when verification failed."""

        return (
            self.failure_type
            == FailureType.VERIFICATION
        )