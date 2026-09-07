from abc import ABC, abstractmethod

from app.config.constants import AssistantMode
from app.intelligence.action import Action
from app.intelligence.action_factory import ActionFactory


class TaskDecomposer(ABC):
    """
    Abstract interface for converting a user goal
    into an ordered sequence of computer actions.
    """

    @abstractmethod
    def decompose(
        self,
        goal: str,
        mode: str = AssistantMode.DO_IT_FOR_ME,
    ) -> list[Action]:
        raise NotImplementedError


class RuleBasedTaskDecomposer(TaskDecomposer):
    """
    Development task decomposer.

    This implementation uses deterministic rules so that
    AURA can develop and test the complete planning pipeline
    before an LLM is connected.

    The interface is intentionally model-independent.
    """

    def decompose(
        self,
        goal: str,
        mode: str = AssistantMode.DO_IT_FOR_ME,
    ) -> list[Action]:

        normalized = self._normalize(goal)

        if not normalized:
            return [
                ActionFactory.speak(
                    "I could not determine what you want me to do."
                )
            ]

        if normalized == "open notepad":
            return self._open_notepad(mode)

        if normalized == "open notepad and type hello world":
            return self._open_notepad_and_type(
                "Hello World"
            )

        if normalized == "open calculator":
            return self._open_calculator()

        return self._unknown_goal(
            goal,
            mode,
        )

    def _open_notepad(
        self,
        mode: str,
    ) -> list[Action]:

        if mode == AssistantMode.SHOW_ME_HOW:
            return [
                ActionFactory.speak(
                    "I will show you how to open Notepad."
                ),
                ActionFactory.press_key(
                    "win",
                    description="Open Windows search",
                ),
                ActionFactory.type_text(
                    "Notepad",
                    description="Search for Notepad",
                    verification={
                        "type": "SCREEN_CONTAINS_TEXT",
                        "text": "Notepad",
                    },
                ),
                ActionFactory.click(
                    "Notepad",
                    description="Open the Notepad result",
                    verification={
                        "type": "APPLICATION_RUNNING",
                        "process": "notepad.exe",
                        "max_attempts": 3,
                        "retry_delay": 0.5,
                    },
                ),
            ]

        return [
            ActionFactory.launch_application(
                "notepad",
                startup_wait=1.0,
                verification={
                    "type": "APPLICATION_RUNNING",
                    "process": "notepad.exe",
                    "max_attempts": 3,
                    "retry_delay": 0.5,
                },
            )
        ]

    def _open_notepad_and_type(
        self,
        text: str,
    ) -> list[Action]:

        return [
            ActionFactory.launch_application(
                "notepad",
                startup_wait=1.0,
                verification={
                    "type": "APPLICATION_RUNNING",
                    "process": "notepad.exe",
                    "max_attempts": 3,
                    "retry_delay": 0.5,
                },
            ),
            ActionFactory.type_text(
                text,
                description=f"Type {text}",
                verification={
                    "type": "SCREEN_CONTAINS_TEXT",
                    "text": text,
                    "max_attempts": 3,
                    "retry_delay": 0.5,
                },
            ),
        ]

    def _open_calculator(
        self,
    ) -> list[Action]:

        return [
            ActionFactory.launch_application(
                "calc",
                startup_wait=1.0,
            )
        ]

    def _unknown_goal(
        self,
        goal: str,
        mode: str,
    ) -> list[Action]:

        if mode == AssistantMode.SHOW_ME_HOW:
            message = (
                f"I do not know how to teach you "
                f"how to {goal} yet."
            )
        else:
            message = (
                f"I do not know how to perform "
                f"{goal} yet."
            )

        return [
            ActionFactory.speak(message)
        ]

    @staticmethod
    def _normalize(
        text: str,
    ) -> str:
        return " ".join(
            text.strip().lower().split()
        )