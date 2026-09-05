from dataclasses import dataclass, field

from app.config.constants import AssistantMode, RiskLevel
from app.intelligence.action import Action


@dataclass
class Task:
    """Represents a complete user request."""

    goal: str

    mode: str = AssistantMode.DO_IT_FOR_ME
    risk_level: str = RiskLevel.LOW

    actions: list[Action] = field(default_factory=list)

    requires_confirmation: bool = False

    metadata: dict = field(default_factory=dict)

    def add_action(self, action: Action) -> None:
        """Add an action to the task."""

        self.actions.append(action)

    @property
    def total_actions(self) -> int:
        """Return the number of actions in the task."""

        return len(self.actions)