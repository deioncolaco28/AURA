from app.config.constants import AssistantMode
from app.intelligence.action import Action, ActionType
from app.intelligence.intent import Intent
from app.intelligence.task import Task


class Planner:
    """Converts an interpreted intent into an executable task."""

    def create_task(self, intent: Intent) -> Task:
        """Create a task from an intent."""

        task = Task(
            goal=intent.goal,
            mode=intent.mode,
            risk_level=intent.risk_level,
            requires_confirmation=intent.requires_confirmation,
        )

        return task