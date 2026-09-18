"""
Tests for DesktopManager.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from app.automation.desktop_manager import DesktopManager
from app.perception.perception_result import PerceptionResult
from app.perception.ui_element import UIElement


class TestDesktopManager:
    def setup_method(self):
        self.mock_mouse = MagicMock()
        self.mock_keyboard = MagicMock()
        self.mock_pm = MagicMock()
        self.mock_sc = MagicMock()

        self.dm = DesktopManager(
            mouse=self.mock_mouse,
            keyboard=self.mock_keyboard,
            perception_manager=self.mock_pm,
            screenshot_capture=self.mock_sc,
        )

    def test_mouse_actions(self):
        self.dm.click(100, 200)
        self.mock_mouse.click.assert_called_once_with(x=100, y=200, button="left")

        self.dm.double_click(150, 250)
        self.mock_mouse.double_click.assert_called_once_with(x=150, y=250)

        self.dm.right_click(300, 400)
        self.mock_mouse.click.assert_called_with(x=300, y=400, button="right")

        self.dm.move_to(50, 60, duration=0.1)
        self.mock_mouse.move_to.assert_called_once_with(x=50, y=60, duration=0.1)

    def test_keyboard_actions(self):
        self.dm.type_text("test text", interval=0.01)
        self.mock_keyboard.type_text.assert_called_once_with(text="test text", interval=0.01)

        self.dm.press_key("enter")
        self.mock_keyboard.press.assert_called_once_with(key="enter")

        self.dm.hotkey("ctrl", "s")
        self.mock_keyboard.hotkey.assert_called_once_with("ctrl", "s")

    def test_window_operations(self):
        self.dm.switch_application()
        self.mock_keyboard.hotkey.assert_called_with("alt", "tab")

        self.dm.minimize_window()
        self.mock_keyboard.hotkey.assert_called_with("win", "down")

        self.dm.maximize_window()
        self.mock_keyboard.hotkey.assert_called_with("win", "up")

        self.dm.close_window()
        self.mock_keyboard.hotkey.assert_called_with("alt", "f4")

    def test_locate_and_click_dynamic_grounding(self):
        # Target element detected dynamically at (400, 300) with size (100, 40)
        elem = UIElement(
            element_id="btn_submit",
            text="Submit Order",
            element_type="button",
            x=350,
            y=280,
            width=100,
            height=40,
            confidence=0.95,
        )
        self.mock_sc.capture.return_value = MagicMock()
        self.mock_pm.analyze.return_value = PerceptionResult(elements=[elem])

        result = self.dm.locate_and_click("Submit Order")
        assert result is not None
        assert result.element_id == "btn_submit"
        # Center should be (400, 300)
        self.mock_mouse.click.assert_called_once_with(x=400, y=300, button="left")
