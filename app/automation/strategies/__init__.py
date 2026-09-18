"""
app/automation/strategies package
"""

from app.automation.strategies.strategy import (
    ActionStrategy,
    StrategyResult,
    DOMStrategy,
    AccessibilityStrategy,
    VisualGroundingStrategy,
    KeyboardShortcutStrategy,
    StrategySelector,
)

__all__ = [
    "ActionStrategy",
    "StrategyResult",
    "DOMStrategy",
    "AccessibilityStrategy",
    "VisualGroundingStrategy",
    "KeyboardShortcutStrategy",
    "StrategySelector",
]
