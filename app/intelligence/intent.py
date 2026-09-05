from dataclasses import dataclass

from app.config.constants import AssistantMode, RiskLevel


@dataclass
class Intent:
    """Represents the interpreted meaning of a user request."""

    raw_text: str

    goal: str

    mode: str = AssistantMode.DO_IT_FOR_ME

    risk_level: str = RiskLevel.LOW

    requires_confirmation: bool = False