from app.core.execution import ExecutionContext
from app.core.failure import FailureInfo, FailureType
from app.core.observation import ScreenObservation
from app.core.replanner import Replanner
from app.intelligence.action import Action, ActionType
from app.intelligence.action_factory import ActionFactory
from app.intelligence.task import Task
from app.perception.grounding import UIGrounder


class RuleBasedReplanner(Replanner):
    """
    Deterministic recovery system.

    Uses the current screen observation to generate
    replacement actions for common failures.
    """

    MIN_GROUNDING_SCORE = 0.65

    def __init__(
        self,
        grounder: UIGrounder | None = None,
    ):
        self.grounder = (
            grounder
            or UIGrounder()
        )

    def replan(
        self,
        task: Task,
        context: ExecutionContext,
        failed_action: Action,
        observation: ScreenObservation,
        failure: FailureInfo | None = None,
    ) -> list[Action]:

        if observation.metadata.get(
            "observation_failed"
        ):
            return []

        if failure is not None:
            if failure.failure_type == (
                FailureType.VERIFICATION
            ):
                return self._replan_verification_failure(
                    failed_action,
                    observation,
                    failure,
                )

        if failed_action.action_type in (
            ActionType.CLICK,
            ActionType.DOUBLE_CLICK,
        ):
            return self._replan_click(
                failed_action,
                observation,
            )

        if failed_action.action_type == (
            ActionType.TYPE_TEXT
        ):
            return self._replan_type_text(
                failed_action,
                observation,
            )

        return []

    def _replan_verification_failure(
        self,
        failed_action: Action,
        observation: ScreenObservation,
        failure: FailureInfo,
    ) -> list[Action]:

        verification_type = (
            failure.verification_type
        )

        print(
            "Verification-aware recovery:",
            verification_type,
        )

        if failed_action.action_type in (
            ActionType.CLICK,
            ActionType.DOUBLE_CLICK,
        ):
            return self._replan_click(
                failed_action,
                observation,
            )

        if failed_action.action_type == (
            ActionType.TYPE_TEXT
        ):
            return self._replan_type_text(
                failed_action,
                observation,
            )

        return []

    def _replan_click(
        self,
        failed_action: Action,
        observation: ScreenObservation,
    ) -> list[Action]:

        target = failed_action.target

        if not target:
            return []

        result = self.grounder.ground(
            observation.elements,
            target,
        )

        if not result.found:
            return []

        if (
            result.score
            < self.MIN_GROUNDING_SCORE
        ):
            return []

        element = result.element

        if element is None:
            return []

        x, y = element.center

        replacement = Action(
            action_type=(
                ActionType.CLICK
                if failed_action.action_type
                == ActionType.CLICK
                else ActionType.DOUBLE_CLICK
            ),
            target=target,
            description=(
                f"Grounded recovery action "
                f"for {target}"
            ),
            parameters={
                "x": x,
                "y": y,
                "width": element.width,
                "height": element.height,
                "grounding_score": result.score,
                "grounding_reason": result.reason,
            },
            metadata={
                "recovery": True,
                "recovery_strategy": (
                    "grounded_target"
                ),
            },
            resolved=True,
        )

        return [replacement]

    def _replan_type_text(
        self,
        failed_action: Action,
        observation: ScreenObservation,
    ) -> list[Action]:

        if failed_action.value is None:
            return []

        text = str(
            failed_action.value
        )

        if not text:
            return []

        if not observation.elements:
            return []

        replacement = ActionFactory.type_text(
            text
        )

        replacement.metadata.update(
            {
                "recovery": True,
                "recovery_strategy": (
                    "text_retry"
                ),
            }
        )

        return [replacement]