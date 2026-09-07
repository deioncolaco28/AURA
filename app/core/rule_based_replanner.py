from app.core.execution import ExecutionContext
from app.core.observation import ScreenObservation
from app.core.replanner import Replanner
from app.intelligence.action import Action, ActionType
from app.intelligence.action_factory import ActionFactory
from app.intelligence.task import Task
from app.perception.grounding import UIGrounder


class RuleBasedReplanner(Replanner):
    """
    Deterministic replanner used during development.

    Recovery decisions are based on the current screen
    observation and the existing AURA grounding system.
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
    ) -> list[Action]:
        """
        Generate replacement actions using the current
        screen observation.
        """

        if observation.metadata.get(
            "observation_failed"
        ):
            return []

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
        """Recover a failed click using UI grounding."""

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

        if failed_action.action_type == (
            ActionType.DOUBLE_CLICK
        ):
            replacement = Action(
                action_type=ActionType.DOUBLE_CLICK,
                target=target,
                description=(
                    f"Grounded recovery double-click "
                    f"for {target}"
                ),
                parameters={
                    "x": element.center[0],
                    "y": element.center[1],
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

        replacement = Action(
            action_type=ActionType.CLICK,
            target=target,
            description=(
                f"Grounded recovery click "
                f"for {target}"
            ),
            parameters={
                "x": element.center[0],
                "y": element.center[1],
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
        """
        Attempt to recover a failed text-entry action.

        Generic text retry is permitted only when the
        screen still appears usable.
        """

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
            text,
            description=(
                f"Grounded recovery type: {text}"
            ),
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