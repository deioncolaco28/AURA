"""
app/automation/strategies/strategy.py

Action strategy abstractions for selecting the most reliable interaction method
(Accessibility, DOM, Visual Grounding, Keyboard Shortcut).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.intelligence.action import Action
from app.perception.ui_element import UIElement


@dataclass
class StrategyResult:
    """Result of an action strategy execution."""

    success: bool
    strategy_name: str
    message: str = ""
    target_element: UIElement | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ActionStrategy(ABC):
    """Abstract base class for an interaction strategy."""

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def can_handle(self, action: Action, element: UIElement | None = None, context: dict[str, Any] | None = None) -> bool:
        """Return True if this strategy can execute the requested action."""
        raise NotImplementedError

    @abstractmethod
    def execute(self, action: Action, element: UIElement | None = None, context: dict[str, Any] | None = None) -> StrategyResult:
        """Execute the action using this strategy."""
        raise NotImplementedError

    def get_priority_score(self, action: Action, element: UIElement | None = None, context: dict[str, Any] | None = None) -> float:
        """Return a priority score [0.0 - 1.0] for deterministic strategy ranking."""
        return 0.5


class DOMStrategy(ActionStrategy):
    """Interacts directly with browser DOM elements using Playwright."""

    def __init__(self, browser_controller: Any = None):
        self.browser_controller = browser_controller

    @property
    def name(self) -> str:
        return "dom"

    def can_handle(self, action: Action, element: UIElement | None = None, context: dict[str, Any] | None = None) -> bool:
        if self.browser_controller is None or not getattr(self.browser_controller, "is_available", lambda: False)():
            return False
        # If element is from DOM source or action specifies browser environment
        if element and element.source.upper() == "DOM":
            return True
        if context and context.get("environment") == "browser":
            return True
        return False

    def get_priority_score(self, action: Action, element: UIElement | None = None, context: dict[str, Any] | None = None) -> float:
        # DOM interactions are highest priority for web content (direct and deterministic)
        return 0.95

    def execute(self, action: Action, element: UIElement | None = None, context: dict[str, Any] | None = None) -> StrategyResult:
        try:
            target = action.target or (element.text if element else "")
            if not target:
                return StrategyResult(success=False, strategy_name=self.name, message="Missing target for DOM action.")

            # Map action type to DOM operation
            act_type = action.action_type.upper()
            if "CLICK" in act_type:
                self.browser_controller.click(target)
            elif "TYPE" in act_type and action.value is not None:
                self.browser_controller.type_text(target, str(action.value))
            elif "SUBMIT" in act_type:
                self.browser_controller.submit(target)
            else:
                self.browser_controller.click(target)

            return StrategyResult(
                success=True,
                strategy_name=self.name,
                message=f"DOM executed {action.action_type} on '{target}'",
                target_element=element,
            )
        except Exception as exc:
            return StrategyResult(success=False, strategy_name=self.name, message=f"DOM error: {exc}")


class AccessibilityStrategy(ActionStrategy):
    """Invokes native OS accessibility / UI Automation nodes."""

    @property
    def name(self) -> str:
        return "accessibility"

    def can_handle(self, action: Action, element: UIElement | None = None, context: dict[str, Any] | None = None) -> bool:
        if element and element.source.upper() in ("ACCESSIBILITY", "UIA", "WINDOWS"):
            return element.is_interactable and element.is_enabled
        return False

    def get_priority_score(self, action: Action, element: UIElement | None = None, context: dict[str, Any] | None = None) -> float:
        return 0.85

    def execute(self, action: Action, element: UIElement | None = None, context: dict[str, Any] | None = None) -> StrategyResult:
        if not element:
            return StrategyResult(success=False, strategy_name=self.name, message="No accessibility element.")
        # Accessibility coordinate or invoke execution
        cx, cy = element.center
        from app.automation.mouse import MouseController
        mouse = MouseController()
        mouse.click(cx, cy)
        return StrategyResult(
            success=True,
            strategy_name=self.name,
            message=f"Accessibility invoked '{element.text or element.element_id}' at ({cx}, {cy})",
            target_element=element,
        )


class VisualGroundingStrategy(ActionStrategy):
    """Uses visual perception coordinates and desktop mouse/keyboard controllers."""

    def __init__(self, desktop_manager: Any = None):
        self.desktop_manager = desktop_manager

    @property
    def name(self) -> str:
        return "visual_grounding"

    def can_handle(self, action: Action, element: UIElement | None = None, context: dict[str, Any] | None = None) -> bool:
        return element is not None and element.confidence >= 0.3

    def get_priority_score(self, action: Action, element: UIElement | None = None, context: dict[str, Any] | None = None) -> float:
        # Fallback priority when direct DOM/UIA is unavailable
        return 0.70

    def execute(self, action: Action, element: UIElement | None = None, context: dict[str, Any] | None = None) -> StrategyResult:
        if not element:
            return StrategyResult(success=False, strategy_name=self.name, message="No visual element to ground.")

        cx, cy = element.center
        from app.automation.mouse import MouseController
        mouse = MouseController()

        act_type = action.action_type.upper()
        if "DOUBLE_CLICK" in act_type:
            mouse.double_click(cx, cy)
        elif "RIGHT_CLICK" in act_type:
            mouse.click(cx, cy, button="right")
        else:
            mouse.click(cx, cy)

        if "TYPE" in act_type and action.value is not None:
            from app.automation.keyboard import KeyboardController
            kbd = KeyboardController()
            kbd.type_text(str(action.value))

        return StrategyResult(
            success=True,
            strategy_name=self.name,
            message=f"Visual grounding executed {action.action_type} at ({cx}, {cy})",
            target_element=element,
        )


class KeyboardShortcutStrategy(ActionStrategy):
    """Executes actions via standard keyboard shortcuts (e.g. Enter, Esc, Ctrl+S, Alt+F4)."""

    SHORTCUT_MAP = {
        "save": ("ctrl", "s"),
        "copy": ("ctrl", "c"),
        "paste": ("ctrl", "v"),
        "select all": ("ctrl", "a"),
        "undo": ("ctrl", "z"),
        "close": ("alt", "f4"),
        "submit": ("enter",),
        "confirm": ("enter",),
        "cancel": ("escape",),
    }

    @property
    def name(self) -> str:
        return "keyboard_shortcut"

    def can_handle(self, action: Action, element: UIElement | None = None, context: dict[str, Any] | None = None) -> bool:
        if action.target and action.target.strip().lower() in self.SHORTCUT_MAP:
            return True
        if action.parameters.get("shortcut"):
            return True
        return False

    def get_priority_score(self, action: Action, element: UIElement | None = None, context: dict[str, Any] | None = None) -> float:
        return 0.75

    def execute(self, action: Action, element: UIElement | None = None, context: dict[str, Any] | None = None) -> StrategyResult:
        from app.automation.keyboard import KeyboardController
        kbd = KeyboardController()

        shortcut = action.parameters.get("shortcut")
        if not shortcut and action.target:
            shortcut = self.SHORTCUT_MAP.get(action.target.strip().lower())

        if not shortcut:
            return StrategyResult(success=False, strategy_name=self.name, message="No shortcut found.")

        kbd.hotkey(*shortcut)
        return StrategyResult(
            success=True,
            strategy_name=self.name,
            message=f"Executed shortcut {shortcut}",
            target_element=element,
        )


class StrategySelector:
    """
    Evaluates available interaction strategies and selects the highest-scoring candidate.
    """

    def __init__(self, strategies: list[ActionStrategy] | None = None):
        self.strategies = strategies or [
            DOMStrategy(),
            AccessibilityStrategy(),
            VisualGroundingStrategy(),
            KeyboardShortcutStrategy(),
        ]

    def select_strategy(
        self,
        action: Action,
        element: UIElement | None = None,
        context: dict[str, Any] | None = None,
    ) -> ActionStrategy | None:
        """Pick the best available strategy for the action and target element."""
        viable = [
            s for s in self.strategies
            if s.can_handle(action, element=element, context=context)
        ]
        if not viable:
            return None

        viable.sort(
            key=lambda s: s.get_priority_score(action, element=element, context=context),
            reverse=True,
        )
        return viable[0]
