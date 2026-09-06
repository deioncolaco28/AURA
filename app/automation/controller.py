import time

from app.automation.applications import ApplicationController
from app.automation.keyboard import KeyboardController
from app.automation.mouse import MouseController


class ComputerController:
    """High-level interface for controlling the computer."""

    def __init__(self):
        self.mouse = MouseController()
        self.keyboard = KeyboardController()
        self.applications = ApplicationController()

    def launch_application(self, application: str) -> None:
        """Launch a desktop application."""

        self.applications.launch(application)

    def move_mouse(
        self,
        x: int,
        y: int,
        duration: float = 0.2,
    ) -> None:
        """Move the mouse."""

        self.mouse.move_to(
            x,
            y,
            duration,
        )

    def click(
        self,
        x: int | None = None,
        y: int | None = None,
        button: str = "left",
    ) -> None:
        """Click the mouse."""

        self.mouse.click(
            x,
            y,
            button,
        )

    def double_click(
        self,
        x: int | None = None,
        y: int | None = None,
    ) -> None:
        """Double-click."""

        self.mouse.double_click(x, y)

    def type_text(
        self,
        text: str,
        interval: float = 0.02,
    ) -> None:
        """Type text."""

        self.keyboard.type_text(
            text,
            interval,
        )

    def press(self, key: str) -> None:
        """Press a keyboard key."""

        self.keyboard.press(key)

    def hotkey(self, *keys: str) -> None:
        """Press a keyboard shortcut."""

        self.keyboard.hotkey(*keys)

    def wait(self, seconds: float) -> None:
        """Wait for a specified amount of time."""

        if seconds < 0:
            raise ValueError("Wait duration cannot be negative.")

        time.sleep(seconds)