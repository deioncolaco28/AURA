from dataclasses import dataclass, field
from typing import Any


class ActionType:
    """Supported computer interaction actions."""

    LAUNCH_APPLICATION = "LAUNCH_APPLICATION"
    CLICK = "CLICK"
    TYPE_TEXT = "TYPE_TEXT"
    PRESS_KEY = "PRESS_KEY"
    MOVE_MOUSE = "MOVE_MOUSE"
    WAIT = "WAIT"
    LOCATE = "LOCATE"
    HIGHLIGHT = "HIGHLIGHT"
    SPEAK = "SPEAK"


@dataclass
class Action:
    """Represents one atomic action AURA can perform."""

    action_type: str

    target: str | None = None
    value: Any = None

    parameters: dict[str, Any] = field(
        default_factory=dict
    )

    description: str | None = None

    verification: dict[str, Any] = field(
        default_factory=dict
    )