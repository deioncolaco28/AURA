from app.automation.controller import ComputerController
from app.intelligence.action import Action, ActionType


class ActionExecutor:
    """Executes validated AURA actions."""

    def __init__(self, controller: ComputerController | None = None):
        self.controller = controller or ComputerController()

    def execute(self, action: Action) -> None:
        """Execute a single action."""

        action_type = action.action_type

        if action_type == ActionType.LAUNCH_APPLICATION:
            self._launch_application(action)

        elif action_type == ActionType.CLICK:
            self._click(action)

        elif action_type == ActionType.TYPE_TEXT:
            self._type_text(action)

        elif action_type == ActionType.PRESS_KEY:
            self._press_key(action)

        elif action_type == ActionType.MOVE_MOUSE:
            self._move_mouse(action)

        elif action_type == ActionType.WAIT:
            self._wait(action)

        else:
            raise ValueError(
                f"Unsupported executable action: {action_type}"
            )

    def _launch_application(self, action: Action) -> None:
        if not action.target:
            raise ValueError(
                "LAUNCH_APPLICATION requires a target."
            )

        self.controller.launch_application(
            action.target
        )

    def _click(self, action: Action) -> None:
        x = action.parameters.get("x")
        y = action.parameters.get("y")

        if x is None or y is None:
            raise ValueError(
                "CLICK currently requires x and y coordinates."
            )

        self.controller.click(x, y)

    def _type_text(self, action: Action) -> None:
        if action.value is None:
            raise ValueError(
                "TYPE_TEXT requires a value."
            )

        self.controller.type_text(
            str(action.value)
        )

    def _press_key(self, action: Action) -> None:
        if not action.value:
            raise ValueError(
                "PRESS_KEY requires a key."
            )

        self.controller.press(
            str(action.value)
        )

    def _move_mouse(self, action: Action) -> None:
        x = action.parameters.get("x")
        y = action.parameters.get("y")

        if x is None or y is None:
            raise ValueError(
                "MOVE_MOUSE requires x and y coordinates."
            )

        self.controller.move_mouse(x, y)

    def _wait(self, action: Action) -> None:
        seconds = action.parameters.get(
            "seconds",
            1.0,
        )

        self.controller.wait(seconds)