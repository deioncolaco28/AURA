import time

from app.automation.browser import BrowserController
from app.automation.controller import ComputerController
from app.intelligence.action import Action, ActionType


class ActionExecutor:
    """Executes validated atomic computer actions."""

    def __init__(
        self,
        controller: ComputerController | None = None,
        browser_controller: BrowserController | None = None,
    ):
        self.controller = (
            controller
            or ComputerController()
        )

        self.browser_controller = (
            browser_controller
            or BrowserController()
        )

    def execute(
        self,
        action: Action,
    ) -> None:
        """Execute one action."""

        action_type = action.action_type

        if action_type == ActionType.LAUNCH_APPLICATION:
            self._launch_application(action)

        elif action_type == ActionType.OPEN_URL:
            self._open_url(action)

        elif action_type == ActionType.CLICK:
            self._click(action)

        elif action_type == ActionType.DOUBLE_CLICK:
            self._double_click(action)

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
                f"Unsupported executable action: "
                f"{action_type}"
            )

    def _launch_application(
        self,
        action: Action,
    ) -> None:
        if not action.target:
            raise ValueError(
                "LAUNCH_APPLICATION "
                "requires a target."
            )

        self.controller.launch_application(
            action.target
        )

        time.sleep(
            action.parameters.get(
                "startup_wait",
                1.0,
            )
        )

    def _open_url(
        self,
        action: Action,
    ) -> None:
        if not action.target:
            raise ValueError(
                "OPEN_URL requires a target."
            )

        result = self.browser_controller.open_url(
            action.target
        )

        action.execution_result.update(
            {
                "browser_success": result.success,
                "url": result.url,
                "message": result.message,
            }
        )

        if not result.success:
            raise RuntimeError(
                result.message
                or "Browser navigation failed."
            )

    def _click(
        self,
        action: Action,
    ) -> None:
        x = action.parameters.get("x")
        y = action.parameters.get("y")

        if x is None or y is None:
            raise ValueError(
                "CLICK requires resolved "
                "x and y coordinates."
            )

        self.controller.click(
            x,
            y,
        )

    def _double_click(
        self,
        action: Action,
    ) -> None:
        x = action.parameters.get("x")
        y = action.parameters.get("y")

        if x is None or y is None:
            raise ValueError(
                "DOUBLE_CLICK requires "
                "resolved x and y coordinates."
            )

        self.controller.double_click(
            x,
            y,
        )

    def _type_text(
        self,
        action: Action,
    ) -> None:
        if action.value is None:
            raise ValueError(
                "TYPE_TEXT requires a value."
            )

        self.controller.type_text(
            str(action.value)
        )

    def _press_key(
        self,
        action: Action,
    ) -> None:
        if not action.value:
            raise ValueError(
                "PRESS_KEY requires a key."
            )

        self.controller.press(
            str(action.value)
        )

    def _move_mouse(
        self,
        action: Action,
    ) -> None:
        x = action.parameters.get("x")
        y = action.parameters.get("y")

        if x is None or y is None:
            raise ValueError(
                "MOVE_MOUSE requires "
                "resolved x and y coordinates."
            )

        self.controller.move_mouse(
            x,
            y,
        )

    def _wait(
        self,
        action: Action,
    ) -> None:
        seconds = action.parameters.get(
            "seconds",
            1.0,
        )

        self.controller.wait(
            seconds
        )