from abc import ABC, abstractmethod

from app.core.execution import ExecutionContext
from app.core.failure import FailureInfo
from app.core.observation import ScreenObservation
from app.intelligence.action import Action
from app.intelligence.task import Task


class Replanner(ABC):
    """
    Base interface for task recovery and replanning.

    A replanner receives:
        - the original task
        - current execution context
        - the failed action
        - the latest screen observation
        - optional structured failure information

    The failure argument is optional to preserve compatibility
    with simpler/custom replanners.
    """

    @abstractmethod
    def replan(
        self,
        task: Task,
        context: ExecutionContext,
        failed_action: Action,
        observation: ScreenObservation,
        failure: FailureInfo | None = None,
    ) -> list[Action]:
        """
        Generate replacement actions.

        Return an empty list when recovery is not possible.
        """
        raise NotImplementedError


class NoOpReplanner(Replanner):
    """
    Default replanner.

    Used when no recovery strategy has been configured.
    """

    def replan(
        self,
        task: Task,
        context: ExecutionContext,
        failed_action: Action,
        observation: ScreenObservation,
        failure: FailureInfo | None = None,
    ) -> list[Action]:
        """
        Do not generate replacement actions.
        """

        return []