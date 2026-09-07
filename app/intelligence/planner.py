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
            requires_confirmation=(
                intent.requires_confirmation
            ),
        )

        for action in self._generate_actions(
            intent
        ):
            task.add_action(action)

        return task

    def _generate_actions(
        self,
        intent: Intent,
    ) -> list[Action]:
        """Generate actions for a recognized goal."""

        goal = intent.goal.strip()
        normalized = goal.lower()

        if normalized == "open notepad":
            return self._open_notepad(
                intent.mode
            )

        if normalized == (
            "open notepad and type hello world"
        ):
            return self._open_notepad_and_type()

        if normalized == "open calculator":
            return self._open_calculator()

        return [
            ActionFactory.speak(
                f"I do not know how to "
                f"{self._verb_for_mode(intent.mode)} "
                f"{goal} yet."
            )
        ]

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
                    description=(
                        "Open Windows search"
                    ),
                ),
                ActionFactory.type_text(
                    "Notepad",
                    description=(
                        "Search for Notepad"
                    ),
                ),
                ActionFactory.click(
                    "Notepad",
                    description=(
                        "Open the Notepad result"
                    ),
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
                description=(
                    "Type Hello World"
                ),
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

    def _verb_for_mode(
        self,
        mode: str,
    ) -> str:
        if mode == AssistantMode.SHOW_ME_HOW:
            return "teach you how to"

        return "perform"