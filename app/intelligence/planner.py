from app.config.constants import AssistantMode
from app.intelligence.action import Action
from app.intelligence.action_factory import ActionFactory
from app.intelligence.intent import Intent
from app.intelligence.task import Task


class Planner:
    """Converts interpreted intent into a structured task."""

    def create_task(
        self,
        intent: Intent,
    ) -> Task:
        """Create a task from an intent."""

        task = Task(
            goal=intent.goal,
            mode=intent.mode,
            risk_level=intent.risk_level,
            requires_confirmation=intent.requires_confirmation,
        )

        actions = self.generate_actions(intent)

        for action in actions:
            task.add_action(action)

        return task

    def generate_actions(
        self,
        intent: Intent,
    ) -> list[Action]:
        """
        Generate an ordered sequence of actions
        for the requested goal.
        """

        goal = intent.goal.strip()

        if not goal:
            return [
                ActionFactory.speak(
                    "I could not determine what you want me to do."
                )
            ]

        normalized = goal.lower()

        if normalized == "open notepad":
            return self._plan_open_notepad(
                intent.mode
            )

        if normalized == "open notepad and type hello world":
            return self._plan_open_notepad_and_type()

        if normalized == "open calculator":
            return self._plan_open_calculator()

        return self._plan_unknown_goal(
            goal,
            intent.mode,
        )

    def _plan_open_notepad(
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

    def _plan_open_notepad_and_type(
        self,
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
                "Hello World",
                description="Type Hello World",
                verification={
                    "type": "SCREEN_CONTAINS_TEXT",
                    "text": "Hello World",
                },
            ),
        ]

    def _plan_open_calculator(
        self,
    ) -> list[Action]:

        return [
            ActionFactory.launch_application(
                "calc",
                startup_wait=1.0,
                verification={
                    "type": "APPLICATION_RUNNING",
                    "process": "CalculatorApp.exe",
                    "max_attempts": 3,
                    "retry_delay": 0.5,
                },
            )
        ]

    def _plan_unknown_goal(
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