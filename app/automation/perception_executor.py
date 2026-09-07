from app.automation.action_executor import ActionExecutor
from app.intelligence.action import Action, ActionType
from app.perception.perception_manager import (
    PerceptionManager,
)
from app.perception.screenshot import ScreenshotCapture
from app.automation.action_resolver import (
    ActionResolver,
)


class PerceptionExecutor:
    """Executes actions using current screen perception."""

    def __init__(
        self,
        action_executor: ActionExecutor | None = None,
        perception_manager: PerceptionManager | None = None,
        action_resolver: ActionResolver | None = None,
        screenshot_capture: ScreenshotCapture | None = None,
    ):
        self.action_executor = (
            action_executor
            or ActionExecutor()
        )

        self.perception_manager = (
            perception_manager
            or PerceptionManager()
        )

        self.action_resolver = (
            action_resolver
            or ActionResolver()
        )

        self.screenshot_capture = (
            screenshot_capture
            or ScreenshotCapture()
        )

    def execute(
        self,
        action: Action,
    ) -> Action:
        """Perceive, resolve, and execute an action."""

        if action.action_type in (
            ActionType.CLICK,
            ActionType.DOUBLE_CLICK,
            ActionType.MOVE_MOUSE,
        ):
            image = (
                self.screenshot_capture.capture()
            )

            perception = (
                self.perception_manager.analyze(
                    image,
                    instruction=(
                        action.description
                        or action.target
                    ),
                )
            )

            action = self.action_resolver.resolve(
                action,
                perception,
            )

        self.action_executor.execute(
            action
        )

        action.execution_result = {
            "success": True,
        }

        return action