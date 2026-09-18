"""
app/intelligence/task_condition.py

Deterministic conditional evaluation for agent task branching and skipping.
Supports common computer-use conditions (e.g. app open/closed, file exists, URL match).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from app.core.observation import ScreenObservation


class ConditionType(str, Enum):
    """Types of practical conditions supported in task branching."""

    APP_IS_OPEN = "APP_IS_OPEN"
    APP_IS_CLOSED = "APP_IS_CLOSED"
    FOLDER_EXISTS = "FOLDER_EXISTS"
    FILE_EXISTS = "FILE_EXISTS"
    URL_MATCHES = "URL_MATCHES"
    TEXT_VISIBLE = "TEXT_VISIBLE"
    CUSTOM = "CUSTOM"


@dataclass
class TaskCondition:
    """
    Evaluates whether a condition holds in the current environment state.
    """

    condition_type: ConditionType
    target: str = ""
    custom_predicate: Callable[[ScreenObservation, Any], bool] | None = None
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def evaluate(
        self,
        observation: ScreenObservation | None = None,
        context: Any = None,
        system_verifier: Any = None,
    ) -> bool:
        """Evaluate the condition against current observation and context."""
        if self.condition_type == ConditionType.CUSTOM and self.custom_predicate:
            try:
                return bool(self.custom_predicate(observation, context))
            except Exception:
                return False

        if self.condition_type == ConditionType.APP_IS_OPEN:
            app_clean = self.target.lower().replace(".exe", "")
            if observation and observation.processes:
                if any(app_clean in p.lower() for p in observation.processes):
                    return True
            if system_verifier and hasattr(system_verifier, "application_verifier"):
                return bool(system_verifier.application_verifier.is_running(self.target))
            return False

        if self.condition_type == ConditionType.APP_IS_CLOSED:
            return not self.evaluate_app_is_open(observation, system_verifier)

        if self.condition_type == ConditionType.FOLDER_EXISTS or self.condition_type == ConditionType.FILE_EXISTS:
            path = self.target
            if context and hasattr(context, "resolve_references"):
                path = context.resolve_references(path)
            return os.path.exists(path)

        if self.condition_type == ConditionType.URL_MATCHES:
            if observation and observation.url:
                return self.target.lower() in observation.url.lower()
            return False

        if self.condition_type == ConditionType.TEXT_VISIBLE:
            if observation and observation.screen_text:
                return self.target.lower() in observation.screen_text.lower()
            return False

        return False

    def evaluate_app_is_open(self, observation: ScreenObservation | None, system_verifier: Any = None) -> bool:
        """Helper to check if target application is running."""
        app_clean = self.target.lower().replace(".exe", "")
        if observation and observation.processes:
            if any(app_clean in p.lower() for p in observation.processes):
                return True
        if system_verifier and hasattr(system_verifier, "application_verifier"):
            return bool(system_verifier.application_verifier.is_running(self.target))
        return False
