from app.automation.action_executor import ActionExecutor
from app.automation.action_resolver import ActionResolver
from app.intelligence.action import Action, ActionType
from app.perception.ocr import TesseractOCR
from app.perception.perception_manager import PerceptionManager
from app.perception.screenshot import ScreenshotCapture
from app.perception.vlm import VLM


class PerceptionExecutor:
    """
    Executes UI actions using current screen perception.

    Pipeline:

        Screenshot
            ↓
        OCR + VLM
            ↓
        PerceptionResult
            ↓
        Grounding
            ↓
        Confidence check
            ↓
        Atomic execution

    If grounding fails, the screen is captured again and
    perception is repeated before the action is rejected.
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
        vlm: VLM | None = None,
        max_perception_attempts: int = 2,
    ):
        self.action_executor = (
            action_executor or ActionExecutor()
        )

        self.screenshot_capture = (
            screenshot_capture or ScreenshotCapture()
        )

        if perception_manager is not None:
            self.perception_manager = perception_manager
        else:
            self.perception_manager = PerceptionManager(
                ocr=TesseractOCR(),
                vlm=vlm,
            )

        self.action_resolver = (
            action_resolver or ActionResolver()
        )

        if max_perception_attempts < 1:
            raise ValueError(
                "max_perception_attempts must be at least 1."
            )

        self.max_perception_attempts = (
            max_perception_attempts
        )

    def execute(self, action: Action) -> Action:
        """Perceive, resolve, and execute one action."""

        if action.action_type in self.UI_ACTION_TYPES:
            return self._execute_ui_action(action)

        self.action_executor.execute(action)

        action.execution_result = {
            "success": True,
            "execution_mode": "direct",
        }

        return action

    def _execute_ui_action(self, action: Action) -> Action:
        if not action.target:
            raise ValueError(
                "UI action requires a target."
            )

        last_error = None

        for attempt in range(
            1,
            self.max_perception_attempts + 1,
        ):
            try:
                print(
                    f"Perception attempt "
                    f"{attempt}/"
                    f"{self.max_perception_attempts}"
                )

                image = self.screenshot_capture.capture()

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

                action = self.action_resolver.resolve(
                    action,
                    perception,
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

                self.action_executor.execute(action)

                action.execution_result = {
                    "success": True,
                    "execution_mode": "perception",
                    "perception_attempt": attempt,
                    "grounding_score": (
                        action.parameters[
                            "grounding_score"
                        ]
                    ),
                    "grounding_source": (
                        action.parameters.get(
                            "grounding_source"
                        )
                    ),
                    "perception_sources": (
                        perception.sources_used
                    ),
                }

                return action

            except (LookupError, ValueError) as error:
                last_error = error

                print(
                    f"Perception attempt {attempt} "
                    f"failed: {error}"
                )

                if attempt < self.max_perception_attempts:
                    print(
                        "Screen will be perceived again."
                    )

        raise LookupError(
            f"Unable to reliably ground "
            f"'{action.target}' after "
            f"{self.max_perception_attempts} "
            f"perception attempts."
        ) from last_error