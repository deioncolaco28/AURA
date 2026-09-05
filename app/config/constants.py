class AssistantMode:
    """Modes supported by AURA."""

    DO_IT_FOR_ME = "DO_IT_FOR_ME"
    SHOW_ME_HOW = "SHOW_ME_HOW"


class AssistantState:
    """Runtime states of the assistant."""

    IDLE = "IDLE"
    LISTENING = "LISTENING"
    UNDERSTANDING = "UNDERSTANDING"
    PLANNING = "PLANNING"
    PERCEIVING = "PERCEIVING"
    ACTING = "ACTING"
    VERIFYING = "VERIFYING"
    RECOVERING = "RECOVERING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class RiskLevel:
    """Risk levels for computer actions."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"