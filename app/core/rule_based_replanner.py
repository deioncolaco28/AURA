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

    TEXT_FIELD_TYPES = {
        "text_field",
        "input",
        "textbox",
        "text_box",
        "editable",
    }

    def __init__(
        self,
        grounder: UIGrounder | None = None,
        target_ranker=None,
    ):
        self.grounder = (
            grounder
            or UIGrounder()
        )
        self.target_ranker = target_ranker

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
            if failure.failure_type == FailureType.VERIFICATION:
                return self._replan_verification_failure(
                    failed_action,
                    observation,
                    failure,
                )
            if failure.failure_type == FailureType.APPLICATION_NOT_FOREGROUND:
                app_target = failure.metadata.get("app_name") or failed_action.target or "application"
                return [
                    Action(
                        action_type=ActionType.FOCUS_APPLICATION,
                        target=app_target,
                        description=f"Switch focus back to '{app_target}'.",
                    ),
                    failed_action,
                ]
            if failure.failure_type == FailureType.APPLICATION_NOT_RUNNING:
                app_target = failure.metadata.get("app_name") or failed_action.target or "application"
                return [
                    Action(
                        action_type=ActionType.LAUNCH_APPLICATION,
                        target=app_target,
                        description=f"Launch '{app_target}'.",
                    ),
                    Action(action_type=ActionType.WAIT, parameters={"seconds": 1.0}),
                    failed_action,
                ]
            if failure.failure_type == FailureType.TARGET_AMBIGUOUS:
                q = failure.metadata.get("clarification_question") or f"Which {failed_action.target} did you mean?"
                return [
                    Action(
                        action_type=ActionType.SPEAK,
                        value=q,
                        description="Ask user for clarification.",
                    )
                ]

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

        if self.target_ranker is not None:
            from app.perception.target_query import TargetQuery
            
            query = TargetQuery(text=target)
            ranking_result = self.target_ranker.rank(observation.elements, query)
            
            if not ranking_result.found:
                return []
            
            if ranking_result.best.score < self.MIN_GROUNDING_SCORE:
                return []
                
            element = ranking_result.best.element
            score = ranking_result.best.score
            reason = ranking_result.best.reason
        else:
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
            score = result.score
            reason = result.reason

        if element is None:
            return []

        x, y = element.center

        if failed_action.action_type == (
            ActionType.DOUBLE_CLICK
        ):
            action_type = (
                ActionType.DOUBLE_CLICK
            )
        else:
            action_type = ActionType.CLICK

        replacement = Action(
            action_type=action_type,
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
                "grounding_score": score,
                "grounding_reason": reason,
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
        Recover TYPE_TEXT by locating a text field
        and clicking it before typing.
        """

        if failed_action.value is None:
            return []

        text = str(
            failed_action.value
        )

        if not text:
            return []

        text_field = (
            self._find_text_field(
                observation
            )
        )

        if text_field is None:
            return []

        x, y = text_field.center

        target = (
            text_field.text
            or text_field.description
            or "text field"
        )

        click_action = Action(
            action_type=ActionType.CLICK,
            target=target,
            description=(
                "Grounded recovery click "
                "for text input."
            ),
            parameters={
                "x": x,
                "y": y,
                "width": text_field.width,
                "height": text_field.height,
            },
            metadata={
                "recovery": True,
                "recovery_strategy": (
                    "grounded_text_field"
                ),
            },
            resolved=True,
        )

        type_action = ActionFactory.type_text(
            text
        )

        type_action.metadata.update(
            {
                "recovery": True,
                "recovery_strategy": (
                    "grounded_text_field"
                ),
            }
        )

        return [
            click_action,
            type_action,
        ]

    def _find_text_field(
        self,
        observation: ScreenObservation,
    ):
        """
        Find the most likely text input element.

        Explicit text-field element types are preferred.
        """

        candidates = []

        for element in observation.elements:

            element_type = str(
                getattr(
                    element,
                    "element_type",
                    "",
                )
            ).lower()

            if element_type in (
                self.TEXT_FIELD_TYPES
            ):
                candidates.append(
                    element
                )

        if not candidates:
            return None

        best = None
        best_score = -1.0

        for element in candidates:

            score = 0.0

            text = getattr(
                element,
                "text",
                None,
            )

            description = getattr(
                element,
                "description",
                None,
            )

            if text:
                score += 0.2

            if description:

                normalized = (
                    description.lower()
                )

                if any(
                    keyword in normalized
                    for keyword in (
                        "search",
                        "input",
                        "text",
                        "name",
                        "address",
                        "message",
                    )
                ):
                    score += 0.5

            width = getattr(
                element,
                "width",
                0,
            )

            height = getattr(
                element,
                "height",
                0,
            )

            if width > height:
                score += 0.3

            if score > best_score:
                best = element
                best_score = score

        return best