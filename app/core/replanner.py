from abc import ABC, abstractmethod

from app.core.execution import ExecutionContext
from app.core.failure import FailureInfo
from app.core.observation import ScreenObservation
from app.intelligence.action import Action
from app.intelligence.task import Task


class Replanner(ABC):
    """
    Abstract interface for recovering from failed actions.

    A future LLM-backed implementation can inspect:

    - the original task
    - execution history
    - current screen observation
    - failed action
    - structured failure information

    and produce a new action sequence.
    """

    @abstractmethod
    def replan(
        self,
        task: Task,
        context: ExecutionContext,
        failed_action: Action,
        observation: ScreenObservation,
        failure: FailureInfo,
    ) -> list[Action]:
        raise NotImplementedError


class NoOpReplanner(Replanner):
    """
    Development replanner that performs no replanning.
    """

    def replan(
        self,
        task: Task,
        context: ExecutionContext,
        failed_action: Action,
        observation: ScreenObservation,
        failure: FailureInfo,
    ) -> list[Action]:
        return []