from dataclasses import dataclass, field
from typing import Any


@dataclass
class TutoringInstruction:
    """Represents one instruction given to the user."""

    message: str

    target: str | None = None

    action_type: str | None = None

    parameters: dict[str, Any] = field(
        default_factory=dict
    )

    completion: dict[str, Any] = field(
        default_factory=dict
    )

    recovery: dict[str, Any] = field(
        default_factory=dict
    )

    completed: bool = False

    attempts: int = 0