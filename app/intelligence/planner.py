from app.config.constants import AssistantMode
from app.intelligence.action import Action
from app.intelligence.intent import Intent
from app.intelligence.task import Task
from app.intelligence.task_decomposer import (
    RuleBasedTaskDecomposer,
    TaskDecomposer,
)


class Planner:
    """
    Converts interpreted intent into a structured task.

    Planning responsibility is separated from task decomposition:
    
        Intent
          ↓
        Planner
          ↓
        TaskDecomposer
          ↓
        Actions
          ↓
        Task
    """

    def __init__(
        self,
        decomposer: TaskDecomposer | None = None,
    ):
        self.decomposer = (
            decomposer
            or RuleBasedTaskDecomposer()
        )

    def create_task(
        self,
        intent: Intent,
    ) -> Task:
        """Create a task from an interpreted intent."""

        task = Task(
            goal=intent.goal,
            mode=intent.mode,
            risk_level=intent.risk_level,
            requires_confirmation=intent.requires_confirmation,
        )

        actions = self.generate_actions(
            intent
        )

        for action in actions:
            task.add_action(action)

        return task

    def generate_actions(
        self,
        intent: Intent,
    ) -> list[Action]:
        """
        Ask the configured decomposer to generate
        an ordered action sequence.
        """

        return self.decomposer.decompose(
            goal=intent.goal,
            mode=intent.mode,
        )