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

        if normalized == "open notepad":
            return [
                Action(
                    action_type=ActionType.LAUNCH_APPLICATION,
                    target="notepad",
                    description="Open Notepad",
                )
            ]

        if normalized == "open calculator":
            return [
                Action(
                    action_type=ActionType.LAUNCH_APPLICATION,
                    target="calc",
                    description="Open Calculator",
                )
            ]

        return [
            Action(
                action_type=ActionType.SPEAK,
                value=f"I do not know how to perform {goal} yet.",
            )
        ]