from app.automation.action_executor import (
    ActionExecutor,
)
from app.automation.action_resolver import (
    ActionResolver,
)
from app.intelligence.action import (
    Action,
    ActionType,
)
from app.perception.ocr import (
    TesseractOCR,
)
from app.perception.perception_manager import (
    PerceptionManager,
)
from app.perception.screenshot import (
    ScreenshotCapture,
)


class PerceptionExecutor:
    """
    Executes UI actions using current screen perception.

    Pipeline:

        Screenshot
            ↓
        OCR / VLM
            ↓
        PerceptionResult
            ↓
        Grounding
            ↓
        Coordinates
            ↓
        Atomic execution
    """

    UI_ACTION_TYPES = (
        ActionType.CLICK,
        ActionType.DOUBLE_CLICK,
        ActionType.MOVE_MOUSE,
    )

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

        self.screenshot_capture = (
            screenshot_capture
            or ScreenshotCapture()
        )

        self.perception_manager = (
            perception_manager
            or PerceptionManager(
                ocr=TesseractOCR()
            )
        )

        self.action_resolver = (
            action_resolver
            or ActionResolver()
        )

    def execute(
        self,
        action: Action,
    ) -> Action:
        """
        Perceive, resolve, and execute one action.
        """

        if action.action_type in self.UI_ACTION_TYPES:
            return self._execute_ui_action(
                action
            )

        self.action_executor.execute(
            action
        )

        action.execution_result = {
            "success": True,
            "execution_mode": "direct",
        }

        return action

    def _execute_ui_action(
        self,
        action: Action,
    ) -> Action:
        if not action.target:
            raise ValueError(
                "UI action requires a target."
            )

        image = (
            self.screenshot_capture.capture()
        )

        instruction = (
            action.description
            or action.target
        )

        perception = (
            self.perception_manager.analyze(
                image,
                instruction=instruction,
            )
        )

        print(
            f"Perception sources: "
            f"{perception.sources_used}"
        )

        print(
            f"Detected UI elements: "
            f"{len(perception.elements)}"
        )

        if perception.screen_description:
            print(
                f"Screen: "
                f"{perception.screen_description}"
            )

        action = (
            self.action_resolver.resolve(
                action,
                perception,
            )
        )

        print(
            f"Resolved target: "
            f"{action.target}"
        )

        print(
            f"Resolved coordinates: "
            f"({action.parameters['x']}, "
            f"{action.parameters['y']})"
        )

        print(
            f"Grounding score: "
            f"{action.parameters['grounding_score']:.2f}"
        )

        self.action_executor.execute(
            action
        )

        action.execution_result = {
            "success": True,
            "execution_mode": "perception",
            "grounding_score": (
                action.parameters[
                    "grounding_score"
                ]
            ),
        }

        return action