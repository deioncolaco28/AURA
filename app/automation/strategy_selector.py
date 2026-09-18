"""
app/automation/strategy_selector.py

Dynamically selects and adapts execution strategies for AURA actions.
Maintains a preferred strategy hierarchy and supports adaptive switching during recovery.
"""

from __future__ import annotations

from typing import Any

from app.intelligence.action import Action, ActionType, StrategyType


class StrategySelector:
    """
    Selects optimal execution strategies based on action type, environment capabilities,
    and prior failure history.
    """

    STRATEGY_HIERARCHY = {
        ActionType.SAVE_DOCUMENT: [
            StrategyType.TRANSACTION,
            StrategyType.UIA,
            StrategyType.KEYBOARD_SHORTCUT,
        ],
        ActionType.LAUNCH_APPLICATION: [
            StrategyType.OS_API,
            StrategyType.TRANSACTION,
        ],
        ActionType.FOCUS_APPLICATION: [
            StrategyType.OS_API,
            StrategyType.UIA,
        ],
        ActionType.CLICK: [
            StrategyType.UIA,
            StrategyType.DOM,
            StrategyType.VISUAL_GROUNDING,
            StrategyType.KEYBOARD_SHORTCUT,
            StrategyType.COORDINATE_MOUSE,
        ],
        ActionType.TYPE_TEXT: [
            StrategyType.UIA,
            StrategyType.KEYBOARD_SHORTCUT,
            StrategyType.DOM,
        ],
        ActionType.NAVIGATE_URL: [
            StrategyType.DOM,
            StrategyType.KEYBOARD_SHORTCUT,
            StrategyType.OS_API,
        ],
        ActionType.CREATE_FILE: [StrategyType.OS_API],
        ActionType.CREATE_FOLDER: [StrategyType.OS_API],
        ActionType.MOVE_FILE: [StrategyType.OS_API],
        ActionType.COPY_FILE: [StrategyType.OS_API],
        ActionType.RENAME_FILE: [StrategyType.OS_API],
        ActionType.DELETE_FILE: [StrategyType.OS_API],
    }

    def select_strategy(
        self,
        action: Action,
        failed_strategies: list[str] | None = None,
        context: Any = None,
    ) -> str:
        """Select the highest-priority viable strategy that has not already failed."""
        failed = set(failed_strategies or [])
        available = self.STRATEGY_HIERARCHY.get(
            action.action_type,
            [StrategyType.OS_API, StrategyType.KEYBOARD_SHORTCUT],
        )

        for strat in available:
            if strat not in failed:
                return strat

        # Fallback to general OS or keyboard
        for default_strat in (StrategyType.OS_API, StrategyType.KEYBOARD_SHORTCUT, StrategyType.VISUAL_GROUNDING):
            if default_strat not in failed:
                return default_strat

        return StrategyType.OS_API

    def get_fallback_strategy(
        self,
        action: Action,
        failed_strategy: str,
        all_failed: list[str] | None = None,
    ) -> str | None:
        """Return the next fallback strategy after a failure, or None if options are exhausted."""
        failed = list(all_failed or [])
        if failed_strategy not in failed:
            failed.append(failed_strategy)

        next_strat = self.select_strategy(action, failed_strategies=failed)
        return next_strat if next_strat not in failed else None
