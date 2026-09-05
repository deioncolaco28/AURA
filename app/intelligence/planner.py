from app.config.constants import AssistantMode
from app.intelligence.action import Action, ActionType
from app.intelligence.intent import Intent
from app.intelligence.task import Task


class Planner:
    """Converts an interpreted intent into a structured task."""

    def create_task(self, intent: Intent) -> Task:
        """Create a task and generate initial actions."""

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
        """Generate actions for a supported intent."""

        goal = intent.goal

        if intent.mode == AssistantMode.SHOW_ME_HOW:
            return [
                Action(
                    action_type=ActionType.SPEAK,
                    value=f"I will show you how to {goal}.",
                )
            ]

        return [
            Action(
                action_type=ActionType.SPEAK,
                value=f"I will help you {goal}.",
            )
        ]