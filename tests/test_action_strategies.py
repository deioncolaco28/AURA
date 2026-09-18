"""
Tests for Action Strategies and StrategySelector.
"""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from app.automation.strategies.strategy import (
    AccessibilityStrategy,
    ActionStrategy,
    DOMStrategy,
    KeyboardShortcutStrategy,
    StrategyResult,
    StrategySelector,
    VisualGroundingStrategy,
)
from app.intelligence.action import Action, ActionType
from app.perception.ui_element import UIElement


class TestActionStrategies:
    def test_dom_strategy_selection(self):
        mock_bc = MagicMock()
        mock_bc.is_available.return_value = True

        dom_strat = DOMStrategy(browser_controller=mock_bc)
        selector = StrategySelector(strategies=[dom_strat, VisualGroundingStrategy()])

        elem = UIElement(
            element_id="dom_1",
            text="Search",
            element_type="button",
            source="DOM",
            x=100,
            y=100,
            width=50,
            height=20,
        )
        action = Action(action_type=ActionType.CLICK, target="Search")

        chosen = selector.select_strategy(action, element=elem)
        assert chosen is not None
        assert chosen.name == "dom"

        res = chosen.execute(action, element=elem)
        assert res.success is True
        mock_bc.click.assert_called_once_with("Search")

    def test_accessibility_strategy_selection(self):
        acc_strat = AccessibilityStrategy()
        selector = StrategySelector(strategies=[acc_strat, VisualGroundingStrategy()])

        elem = UIElement(
            element_id="acc_1",
            text="OK",
            element_type="button",
            source="accessibility",
            is_interactable=True,
            is_enabled=True,
            x=200,
            y=300,
            width=60,
            height=30,
        )
        action = Action(action_type=ActionType.CLICK, target="OK")

        chosen = selector.select_strategy(action, element=elem)
        assert chosen is not None
        assert chosen.name == "accessibility"

    def test_keyboard_shortcut_strategy(self):
        k_strat = KeyboardShortcutStrategy()
        action_save = Action(action_type=ActionType.HOTKEY, target="save")

        assert k_strat.can_handle(action_save) is True

    def test_visual_grounding_fallback(self):
        selector = StrategySelector(strategies=[
            DOMStrategy(),
            AccessibilityStrategy(),
            VisualGroundingStrategy(),
        ])

        elem_ocr = UIElement(
            element_id="ocr_1",
            text="Settings",
            element_type="button",
            source="OCR",
            confidence=0.85,
            x=500,
            y=100,
            width=80,
            height=30,
        )
        action = Action(action_type=ActionType.CLICK, target="Settings")

        chosen = selector.select_strategy(action, element=elem_ocr)
        assert chosen is not None
        assert chosen.name == "visual_grounding"
