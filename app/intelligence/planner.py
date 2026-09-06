from app.config.constants import AssistantMode
from app.intelligence.action import Action, ActionType
from app.intelligence.intent import Intent
from app.intelligence.task import Task


class Planner:
    """Converts an interpreted intent into a structured task."""

    def create_task(self, intent: Intent) -> Task:
        """Create a task and generate actions."""

        task = Task(
            goal=intent.goal,
            mode=intent.mode,
            risk_level=intent.risk_level,
            requires_confirmation=intent.requires_confirmation,
        )

        actions = self._generate_actions(intent)

        for action in actions:
            task.add_action(action)

        return task

    def _generate_actions(
        self,
        intent: Intent,
    ) -> list[Action]:
        """Generate actions for supported intents."""

        goal = intent.goal.strip()
        normalized = goal.lower()

        if intent.mode == AssistantMode.SHOW_ME_HOW:
            return [
                Action(
                    action_type=ActionType.SPEAK,
                    value=f"I will show you how to {goal}.",
                )
            ]

        # Multi-step Notepad task
        if normalized == "open notepad and type hello world":
            return [
                Action(
                    action_type=ActionType.LAUNCH_APPLICATION,
                    target="notepad",
                    description="Open Notepad",
                    parameters={
                        "startup_wait": 1.0,
                    },
                    verification={
                        "type": "APPLICATION_RUNNING",
                        "process": "notepad.exe",
                        "max_attempts": 3,
                        "retry_delay": 0.5,
                    },
                ),
                Action(
                    action_type=ActionType.TYPE_TEXT,
                    value="Hello World",
                    description="Type Hello World",
                ),
            ]

        # Single-step Notepad task
        if normalized == "open notepad":
            return [
                Action(
                    action_type=ActionType.LAUNCH_APPLICATION,
                    target="notepad",
                    description="Open Notepad",
                    parameters={
                        "startup_wait": 1.0,
                    },
                    verification={
                        "type": "APPLICATION_RUNNING",
                        "process": "notepad.exe",
                        "max_attempts": 3,
                        "retry_delay": 0.5,
                    },
                )
            ]

        # Single-step Calculator task
        if normalized == "open calculator":
            return [
                Action(
                    action_type=ActionType.LAUNCH_APPLICATION,
                    target="calc",
                    description="Open Calculator",
                    parameters={
                        "startup_wait": 1.0,
                    },
                )
            ]

        # Unsupported task
        return [
            Action(
                action_type=ActionType.SPEAK,
                value=f"I do not know how to perform {goal} yet.",
            )
        ]