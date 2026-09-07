from app.core.execution import ExecutionContext
from app.core.observation import ScreenObservation
from app.core.replanner import Replanner
from app.intelligence.action import Action, ActionType
from app.intelligence.action_factory import ActionFactory
from app.intelligence.task import Task


class RuleBasedReplanner(Replanner):
    """
    Deterministic replanner used during development.

    The replanner examines the current screen observation
    and attempts to recover simple UI actions.

    This provides a model-independent recovery mechanism
    before an LLM-backed replanner is introduced.
    """

    def replan(
        self,
        task: Task,
        context: ExecutionContext,
        failed_action: Action,
        observation: ScreenObservation,
    ) -> list[Action]:
        """
        Generate replacement actions based on the
        current screen observation.
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
        """Attempt to recover a failed click."""

        target = failed_action.target

        if not target:
            return []

        element = self._find_matching_element(
            target,
            observation,
        )

        if element is None:
            return []

        if failed_action.action_type == (
            ActionType.DOUBLE_CLICK
        ):
            replacement = ActionFactory.click(
                target=target,
                description=(
                    f"Recovery click for {target}"
                ),
            )

            return [replacement]

        replacement = ActionFactory.click(
            target=target,
            description=(
                f"Retry click for {target}"
            ),
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

        return [
            ActionFactory.type_text(
                text,
                description=(
                    f"Recovery type: {text}"
                ),
            )
        ]

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