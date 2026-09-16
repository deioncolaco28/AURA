from abc import ABC, abstractmethod

from app.core.execution import ExecutionContext
from app.core.failure import FailureInfo
from app.core.observation import ScreenObservation
from app.intelligence.action import Action
from app.intelligence.task import Task


class Replanner(ABC):
    """
    Interface for generating replacement actions after
    an action fails.
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

        `failure` is optional for backward compatibility with
        older replanners while the recovery architecture is
        being upgraded.
        """
        raise NotImplementedError


class NoOpReplanner(Replanner):
    """
    Default replanner that performs no recovery.
    """

    def replan(
        self,
        task: Task,
        context: ExecutionContext,
        failed_action: Action,
        observation: ScreenObservation,
        failure: FailureInfo | None = None,
    ) -> list[Action]:
        return []