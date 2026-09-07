from app.intelligence.action import Action, ActionType
from app.perception.grounding import UIGrounder
from app.perception.perception_result import (
    PerceptionResult,
)


class ActionResolver:
    """Resolves abstract UI actions into concrete coordinates."""

    def __init__(
        self,
        grounder: UIGrounder | None = None,
    ):
        self.grounder = (
            grounder
            or UIGrounder()
        )

    def resolve(
        self,
        action: Action,
        perception: PerceptionResult,
    ) -> Action:
        """Resolve an action using perceived UI elements."""

        if action.action_type not in (
            ActionType.CLICK,
            ActionType.DOUBLE_CLICK,
            ActionType.MOVE_MOUSE,
        ):
            return action

        if not action.target:
            raise ValueError(
                "UI action requires a target."
            )

        result = self.grounder.ground(
            perception.elements,
            action.target,
        )

        if not result.found:
            raise LookupError(
                f"Could not locate UI target: "
                f"{action.target}"
            )

        if result.score < 0.65:
            raise LookupError(
                f"UI target confidence too low: "
                f"{action.target} "
                f"({result.score:.2f})"
            )

        element = result.element

        action.parameters.update(
            {
                "x": element.center[0],
                "y": element.center[1],
                "width": element.width,
                "height": element.height,
                "grounding_score": result.score,
                "grounding_reason": result.reason,
            }
        )

        action.resolved = True

        return action