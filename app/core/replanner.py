from abc import ABC, abstractmethod

from app.core.execution import ExecutionContext
from app.intelligence.action import Action
from app.intelligence.task import Task


class Replanner(ABC):
    """
    Abstract interface for recovering from failed actions.

    A future LLM-backed implementation can inspect the task,
    execution history, screen state, and failure information
    and produce a new action sequence.
    """

    @abstractmethod
    def replan(
        self,
        task: Task,
        context: ExecutionContext,
        failed_action: Action,
    ) -> list[Action]:
        raise NotImplementedError


class NoOpReplanner(Replanner):
    """
    Development replanner that performs no replanning.

    This keeps the execution engine compatible with the
    existing retry behavior while establishing the interface
    for future intelligent recovery.
    """

    def replan(
        self,
        task: Task,
        context: ExecutionContext,
        failed_action: Action,
    ) -> list[Action]:
        return []