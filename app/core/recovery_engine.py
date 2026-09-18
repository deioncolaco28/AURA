"""
app/core/recovery_engine.py

Deterministic recovery engine and hierarchical policy router for AURA.
Implements the 10-tier deterministic recovery hierarchy without random behavior or infinite loops.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.core.failure import FailureInfo, FailureType
from app.core.observation import ScreenObservation
from app.intelligence.action import Action, ActionType


class RecoveryStrategyType(str, Enum):
    """Hierarchy of deterministic recovery strategies."""

    REOBSERVE = "REOBSERVE"
    REGROUND = "REGROUND"
    FOCUS_APPLICATION = "FOCUS_APPLICATION"
    RETRY = "RETRY"
    ALTERNATE_STRATEGY = "ALTERNATE_STRATEGY"
    SCROLL_SEARCH = "SCROLL_SEARCH"
    LOCAL_REPLAN = "LOCAL_REPLAN"
    GLOBAL_REPLAN = "GLOBAL_REPLAN"
    ASK_USER = "ASK_USER"
    FAIL_SAFELY = "FAIL_SAFELY"


@dataclass
class RecoveryPlan:
    """Action sequence and metadata produced by the recovery engine."""

    strategy: RecoveryStrategyType
    actions: list[Action] = field(default_factory=list)
    explanation: str = ""
    can_continue: bool = True


class RecoveryEngine:
    """
    Executes the 10-tier deterministic recovery hierarchy based on FailureInfo.
    """

    MAX_RETRIES = 2

    def __init__(self, replanner: Any = None):
        self.replanner = replanner

    def plan_recovery(
        self,
        failure: FailureInfo,
        observation: ScreenObservation | None = None,
        context: Any = None,
    ) -> RecoveryPlan:
        """Generate a recovery plan for the classified failure."""
        ftype = failure.failure_type
        action = failure.action
        attempt = failure.attempt

        # -------------------------------------------------------------
        # Tier 9: Ambiguity & Permissions -> ASK USER IMMEDIATELY
        # -------------------------------------------------------------
        if ftype == FailureType.TARGET_AMBIGUOUS:
            question = failure.metadata.get("clarification_question") or f"Which '{action.target}' did you mean?"
            return RecoveryPlan(
                strategy=RecoveryStrategyType.ASK_USER,
                actions=[
                    Action(
                        action_type=ActionType.SPEAK,
                        value=question,
                        description="Ask user to clarify ambiguous target.",
                    )
                ],
                explanation="Target is ambiguous; prompted user for clarification.",
                can_continue=False,
            )

        if ftype == FailureType.PERMISSION_REQUIRED:
            msg = "This operation requires elevated permissions. Please confirm or perform this step manually."
            return RecoveryPlan(
                strategy=RecoveryStrategyType.ASK_USER,
                actions=[
                    Action(
                        action_type=ActionType.SPEAK,
                        value=msg,
                        description="Request user permission.",
                    )
                ],
                explanation="Operation requires user permission.",
                can_continue=False,
            )

        # -------------------------------------------------------------
        # Tier 3: Application Not In Foreground -> FOCUS
        # -------------------------------------------------------------
        if ftype == FailureType.APPLICATION_NOT_FOREGROUND:
            app_target = failure.metadata.get("app_name") or action.target or "application"
            return RecoveryPlan(
                strategy=RecoveryStrategyType.FOCUS_APPLICATION,
                actions=[
                    Action(
                        action_type=ActionType.FOCUS_APPLICATION,
                        target=app_target,
                        description=f"Refocus '{app_target}'.",
                    ),
                    action,
                ],
                explanation=f"Application '{app_target}' was not foreground; refocused and re-queued action.",
                can_continue=True,
            )

        # -------------------------------------------------------------
        # Tier 8: Application Not Running / Crashed -> LAUNCH & WAIT
        # -------------------------------------------------------------
        if ftype in (FailureType.APPLICATION_NOT_RUNNING, FailureType.APPLICATION_CRASHED):
            app_target = failure.metadata.get("app_name") or action.target or "application"
            return RecoveryPlan(
                strategy=RecoveryStrategyType.GLOBAL_REPLAN,
                actions=[
                    Action(
                        action_type=ActionType.LAUNCH_APPLICATION,
                        target=app_target,
                        description=f"Launch application '{app_target}'.",
                    ),
                    Action(action_type=ActionType.WAIT, parameters={"seconds": 1.0}),
                    action,
                ],
                explanation=f"Application '{app_target}' was not running; launched and re-queued action.",
                can_continue=True,
            )

        # -------------------------------------------------------------
        # Tier 1 & 2: Target Not Found / Moved -> REOBSERVE & REGROUND
        # -------------------------------------------------------------
        if ftype in (FailureType.TARGET_NOT_FOUND, FailureType.TARGET_MOVED):
            if attempt <= self.MAX_RETRIES:
                if self.replanner and observation:
                    from app.intelligence.task import Task
                    from app.core.execution import ExecutionContext
                    task_dummy = Task(goal="Recovery")
                    ctx_dummy = ExecutionContext(goal="Recovery", total_steps=1)
                    recovered = self.replanner.replan(task_dummy, ctx_dummy, action, observation, failure=failure)
                    if recovered:
                        return RecoveryPlan(
                            strategy=RecoveryStrategyType.REGROUND,
                            actions=recovered,
                            explanation=f"Re-grounded target '{action.target}' via visual perception.",
                            can_continue=True,
                        )

                # Fallback: re-attempt action with visual locate
                return RecoveryPlan(
                    strategy=RecoveryStrategyType.REOBSERVE,
                    actions=[action],
                    explanation=f"Re-observing screen to locate target '{action.target}'.",
                    can_continue=True,
                )

        # -------------------------------------------------------------
        # Tier 5: Alternate Strategy (e.g. click -> keyboard hotkey / shortcut)
        # -------------------------------------------------------------
        if ftype == FailureType.TARGET_NOT_INTERACTABLE:
            if action.action_type == ActionType.CLICK:
                return RecoveryPlan(
                    strategy=RecoveryStrategyType.ALTERNATE_STRATEGY,
                    actions=[
                        Action(
                            action_type=ActionType.HOTKEY,
                            value="enter",
                            description="Fallback to keyboard Enter.",
                        )
                    ],
                    explanation="Click target not interactable; fell back to keyboard Enter shortcut.",
                    can_continue=True,
                )

        # -------------------------------------------------------------
        # Tier 7 & 8: Local / Global Replanning
        # -------------------------------------------------------------
        if ftype == FailureType.EXPECTED_STATE_NOT_REACHED and self.replanner and observation:
            from app.intelligence.task import Task
            from app.core.execution import ExecutionContext
            task_dummy = Task(goal="Recovery")
            ctx_dummy = ExecutionContext(goal="Recovery", total_steps=1)
            replanned = self.replanner.replan(task_dummy, ctx_dummy, action, observation, failure=failure)
            if replanned:
                return RecoveryPlan(
                    strategy=RecoveryStrategyType.LOCAL_REPLAN,
                    actions=replanned,
                    explanation="Replanned replacement actions based on observation diff.",
                    can_continue=True,
                )

        # -------------------------------------------------------------
        # Tier 10: Fail Safely when retries exceeded or unrecoverable
        # -------------------------------------------------------------
        return RecoveryPlan(
            strategy=RecoveryStrategyType.FAIL_SAFELY,
            actions=[],
            explanation=f"Cannot recover from {ftype} (attempt {attempt}/{self.MAX_RETRIES}). Stopping safely.",
            can_continue=False,
        )
