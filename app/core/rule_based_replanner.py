from app.core.execution import ExecutionContext
from app.core.failure import FailureInfo
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
        failure: FailureInfo,
    ) -> list[Action]:
        """
        Generate replacement actions using the current
        screen observation and structured failure data.
        """

        if observation.metadata.get(
            "observation_failed"
        ):
            return []

        if failure.is_verification_failure:
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
        """
        Recover from a failed verification.

        For now, verification failures use a conservative
        retry strategy. Later stages can use the verification
        type and screen state to choose a more intelligent
        replacement sequence.
        """

        verification_type = (
            failure.verification_type
        )

        print(
            f"Verification-aware recovery: "
            f"{verification_type}"
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

        A generic retry is allowed only when the current
        screen still contains detectable UI elements.
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

    @staticmethod
    def _find_matching_element(
        target: str,
        observation: ScreenObservation,
    ):
        """
        Find a UI element whose text or description
        matches the failed action target.
        """

        normalized_target = (
            target.strip().lower()
        )

        if not normalized_target:
            return None

        exact_match = None
        partial_match = None

        for element in observation.elements:

            candidates = [
                element.text,
                element.description,
                element.attributes.get(
                    "name"
                ),
                element.attributes.get(
                    "label"
                ),
            ]

            for candidate in candidates:
                if not candidate:
                    continue

                normalized_candidate = (
                    str(candidate)
                    .strip()
                    .lower()
                )

                if (
                    normalized_candidate
                    == normalized_target
                ):
                    exact_match = element
                    break

                if (
                    normalized_target
                    in normalized_candidate
                ):
                    partial_match = element

            if exact_match is not None:
                break

        return (
            exact_match
            or partial_match
        )