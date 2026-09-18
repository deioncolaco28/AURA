"""
app/automation/environments/desktop_environment.py

Desktop execution environment for Windows OS mouse, keyboard, and window operations.
"""

from __future__ import annotations

from typing import Any
from app.automation.environments.environment import Environment, EnvironmentCapability


class DesktopEnvironment(Environment):
    """
    Execution environment for desktop OS interactions (mouse, keyboard, shortcuts).
    """

    def __init__(self, desktop_manager: Any = None):
        self._desktop_manager = desktop_manager

    @property
    def name(self) -> str:
        return "desktop"

    def supported_capabilities(self) -> set[EnvironmentCapability]:
        return {
            EnvironmentCapability.MOUSE_CLICK,
            EnvironmentCapability.MOUSE_DOUBLE_CLICK,
            EnvironmentCapability.MOUSE_RIGHT_CLICK,
            EnvironmentCapability.MOUSE_MOVE,
            EnvironmentCapability.MOUSE_DRAG,
            EnvironmentCapability.MOUSE_SCROLL,
            EnvironmentCapability.KEYBOARD_TYPE,
            EnvironmentCapability.KEYBOARD_PRESS,
            EnvironmentCapability.KEYBOARD_HOTKEY,
            EnvironmentCapability.VISUAL_LOCATE,
        }

    @property
    def desktop_manager(self) -> Any:
        if self._desktop_manager is None:
            from app.automation.desktop_manager import DesktopManager
            self._desktop_manager = DesktopManager()
        return self._desktop_manager

    def click(self, x: int | None = None, y: int | None = None, button: str = "left") -> None:
        self.desktop_manager.click(x=x, y=y, button=button)

    def double_click(self, x: int | None = None, y: int | None = None) -> None:
        self.desktop_manager.double_click(x=x, y=y)

    def right_click(self, x: int | None = None, y: int | None = None) -> None:
        self.desktop_manager.right_click(x=x, y=y)

    def move_mouse(self, x: int, y: int, duration: float = 0.2) -> None:
        self.desktop_manager.move_to(x, y, duration)

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.5) -> None:
        self.desktop_manager.drag_and_drop((start_x, start_y), (end_x, end_y), duration=duration)

    def scroll(self, delta: int) -> None:
        self.desktop_manager.scroll(delta)

    def type_text(self, text: str, interval: float = 0.02) -> None:
        self.desktop_manager.type_text(text, interval)

    def press_key(self, key: str) -> None:
        self.desktop_manager.press_key(key)

    def hotkey(self, *keys: str) -> None:
        self.desktop_manager.hotkey(*keys)
