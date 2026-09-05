from dataclasses import dataclass, field
from typing import Any

from app.config.constants import AssistantState


@dataclass
class AssistantState:
    """Stores the current runtime state of AURA."""

    current_state: str = AssistantState.IDLE
    current_mode: str | None = None

    current_task: str | None = None

    current_step: int = 0
    total_steps: int = 0

    last_action: dict[str, Any] | None = None
    last_error: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)