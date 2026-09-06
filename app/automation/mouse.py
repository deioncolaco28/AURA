import pyautogui


class MouseController:
    """Controls the system mouse."""

    def move_to(self, x: int, y: int, duration: float = 0.2) -> None:
        """Move the mouse to a screen coordinate."""

        pyautogui.moveTo(
            x,
            y,
            duration=duration,
        )

    def click(
        self,
        x: int | None = None,
        y: int | None = None,
        button: str = "left",
    ) -> None:
        """Click the mouse."""

        if x is not None and y is not None:
            pyautogui.click(
                x=x,
                y=y,
                button=button,
            )
        else:
            pyautogui.click(button=button)

    def double_click(
        self,
        x: int | None = None,
        y: int | None = None,
    ) -> None:
        """Double-click."""

        if x is not None and y is not None:
            pyautogui.doubleClick(x=x, y=y)
        else:
            pyautogui.doubleClick()

    def get_position(self) -> tuple[int, int]:
        """Return the current mouse position."""

        position = pyautogui.position()

        return position.x, position.y