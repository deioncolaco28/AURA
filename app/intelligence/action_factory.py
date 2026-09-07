from typing import Any

from app.intelligence.action import Action, ActionType


class ActionFactory:
    """Creates standardized AURA actions."""

    @staticmethod
    def speak(
        message: str,
    ) -> Action:

        return Action(
            action_type=ActionType.SPEAK,
            value=message,
        )

    @staticmethod
    def click(
        target: str,
        description: str | None = None,
        verification: dict[str, Any] | None = None,
    ) -> Action:

        return Action(
            action_type=ActionType.CLICK,
            target=target,
            description=description,
            verification=verification or {},
        )

    @staticmethod
    def type_text(
        text: str,
        description: str | None = None,
        verification: dict[str, Any] | None = None,
    ) -> Action:

        return Action(
            action_type=ActionType.TYPE_TEXT,
            value=text,
            description=description,
            verification=verification or {},
        )

    @staticmethod
    def press_key(
        key: str,
        description: str | None = None,
        verification: dict[str, Any] | None = None,
    ) -> Action:

        return Action(
            action_type=ActionType.PRESS_KEY,
            value=key,
            description=description,
            verification=verification or {},
        )

    @staticmethod
    def launch_application(
        application: str,
        startup_wait: float = 1.0,
        verification: dict[str, Any] | None = None,
    ) -> Action:

        return Action(
            action_type=ActionType.LAUNCH_APPLICATION,
            target=application,
            parameters={
                "startup_wait": startup_wait
            },
            verification=verification or {},
        )

    @staticmethod
    def wait(
        seconds: float = 1.0,
    ) -> Action:

        return Action(
            action_type=ActionType.WAIT,
            parameters={
                "seconds": seconds
            },
        )