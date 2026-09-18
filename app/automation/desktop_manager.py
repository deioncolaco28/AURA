"""
app/automation/desktop_manager.py

Coordinates mouse, keyboard, window, and visual desktop automation.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from app.automation.keyboard import KeyboardController
from app.automation.mouse import MouseController
from app.perception.perception_manager import PerceptionManager
from app.perception.screenshot import ScreenshotCapture
from app.perception.target_query import TargetQuery, parse_target_query
from app.perception.ui_element import UIElement

logger = logging.getLogger(__name__)


class DesktopManager:
    """
    High-level desktop manager providing mouse, keyboard, and window automation.
    Integrates visual perception and grounding for target-based interactions without hardcoding coordinates.
    """

    def __init__(
        self,
        mouse: MouseController | None = None,
        keyboard: KeyboardController | None = None,
        perception_manager: PerceptionManager | None = None,
        screenshot_capture: ScreenshotCapture | None = None,
    ):
        self.mouse = mouse or MouseController()
        self.keyboard = keyboard or KeyboardController()
        self.perception_manager = perception_manager or PerceptionManager()
        self.screenshot_capture = screenshot_capture or ScreenshotCapture()

    # ----------------------------------------------------------------------
    # Mouse Operations
    # ----------------------------------------------------------------------

    def click(self, x: int | None = None, y: int | None = None, button: str = "left") -> None:
        """Click at (x, y) or current mouse position."""
        self.mouse.click(x=x, y=y, button=button)

    def double_click(self, x: int | None = None, y: int | None = None) -> None:
        """Double-click at (x, y) or current position."""
        self.mouse.double_click(x=x, y=y)

    def right_click(self, x: int | None = None, y: int | None = None) -> None:
        """Right-click at (x, y) or current position."""
        self.mouse.click(x=x, y=y, button="right")

    def move_to(self, x: int, y: int, duration: float = 0.2) -> None:
        """Move cursor smoothly to (x, y)."""
        self.mouse.move_to(x=x, y=y, duration=duration)

    def drag_and_drop(
        self,
        source: tuple[int, int],
        target: tuple[int, int],
        duration: float = 0.5,
    ) -> None:
        """Drag from source (x, y) to target (x, y)."""
        try:
            import pyautogui  # type: ignore
            pyautogui.moveTo(source[0], source[1])
            pyautogui.dragTo(target[0], target[1], duration=duration, button="left")
        except Exception:
            # Fallback using mouse controller
            self.mouse.move_to(source[0], source[1], duration=0.1)
            self.mouse.click(source[0], source[1])
            self.mouse.move_to(target[0], target[1], duration=duration)
            self.mouse.click(target[0], target[1])

    def scroll(self, delta: int) -> None:
        """Scroll vertically (positive up, negative down)."""
        try:
            import pyautogui  # type: ignore
            pyautogui.scroll(delta)
        except Exception as exc:
            logger.debug(f"Scroll fallback execution: {exc}")

    # ----------------------------------------------------------------------
    # Keyboard Operations
    # ----------------------------------------------------------------------

    def type_text(self, text: str, interval: float = 0.02) -> None:
        """Type text string."""
        self.keyboard.type_text(text=text, interval=interval)

    def press_key(self, key: str) -> None:
        """Press a keyboard key."""
        self.keyboard.press(key=key)

    def hotkey(self, *keys: str) -> None:
        """Press a key combination (e.g. 'ctrl', 'c')."""
        self.keyboard.hotkey(*keys)

    # ----------------------------------------------------------------------
    # Window & Application Control
    # ----------------------------------------------------------------------

    def focus_window(self, title_or_app: str) -> bool:
        """Focus top-level window matching title or application name."""
        try:
            import ctypes
            user32 = ctypes.windll.user32

            # Try to match window title via EnumWindows
            found_hwnd = None
            target_lower = title_or_app.lower()

            def enum_proc(hwnd, lparam):
                nonlocal found_hwnd
                if not user32.IsWindowVisible(hwnd):
                    return True
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value.lower()
                    if target_lower in title:
                        found_hwnd = hwnd
                        return False
                return True

            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            user32.EnumWindows(WNDENUMPROC(enum_proc), 0)

            if found_hwnd:
                user32.ShowWindow(found_hwnd, 9)  # SW_RESTORE
                user32.SetForegroundWindow(found_hwnd)
                return True
        except Exception as exc:
            logger.debug(f"Focus window failed: {exc}")

        # Fallback to Alt+Tab
        self.hotkey("alt", "tab")
        return False

    def minimize_window(self, title_or_app: str | None = None) -> bool:
        """Minimize window (Win+Down or Win+M)."""
        self.hotkey("win", "down")
        return True

    def maximize_window(self, title_or_app: str | None = None) -> bool:
        """Maximize window (Win+Up)."""
        self.hotkey("win", "up")
        return True

    def restore_window(self, title_or_app: str | None = None) -> bool:
        """Restore window size."""
        self.hotkey("win", "down")
        return True

    def close_window(self, title_or_app: str | None = None) -> bool:
        """Close active window (Alt+F4)."""
        self.hotkey("alt", "f4")
        return True

    def switch_application(self) -> None:
        """Switch to next application (Alt+Tab)."""
        self.hotkey("alt", "tab")

    # ----------------------------------------------------------------------
    # Visual Perception Grounded Interaction
    # ----------------------------------------------------------------------

    def locate_and_click(
        self,
        query: TargetQuery | str,
        button: str = "left",
        double: bool = False,
    ) -> UIElement | None:
        """
        Dynamically ground visual target via perception and click its center coordinates.
        Never relies on hardcoded screen coordinates.
        """
        if isinstance(query, str):
            target_query = parse_target_query(query)
        else:
            target_query = query

        screenshot = self.screenshot_capture.capture()
        result = self.perception_manager.analyze(screenshot)

        from app.intelligence.target_ranker import TargetRanker
        ranker = TargetRanker()
        ranked = ranker.rank(result.elements, query=target_query)

        if not ranked.found or ranked.best is None:
            logger.warning(f"Could not locate visual target for query: {target_query}")
            return None

        target_elem = ranked.best.element
        cx, cy = target_elem.center

        if double:
            self.double_click(x=cx, y=cy)
        elif button == "right":
            self.right_click(x=cx, y=cy)
        else:
            self.click(x=cx, y=cy, button=button)

        return target_elem
