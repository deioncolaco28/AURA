"""
Tests for RecoveryEngine and deterministic recovery hierarchy.
"""

from __future__ import annotations

import pytest

from app.core.failure import FailureInfo, FailureType
from app.core.recovery_engine import RecoveryEngine, RecoveryStrategyType
from app.intelligence.action import Action, ActionType


class TestRecoveryEngine:
    def setup_method(self):
        self.engine = RecoveryEngine()

    def test_recovery_ambiguity_asks_user(self):
        act = Action(action_type=ActionType.CLICK, target="Edit")
        failure = FailureInfo(
            action=act,
            failure_type=FailureType.TARGET_AMBIGUOUS,
            metadata={"clarification_question": "Which Edit button would you like to click?"},
        )

        plan = self.engine.plan_recovery(failure)
        assert plan.strategy == RecoveryStrategyType.ASK_USER
        assert plan.can_continue is False
        assert len(plan.actions) == 1
        assert plan.actions[0].action_type == ActionType.SPEAK
        assert "Which Edit button" in plan.actions[0].value

    def test_recovery_application_not_foreground_focuses(self):
        act = Action(action_type=ActionType.CLICK, target="Save")
        failure = FailureInfo(
            action=act,
            failure_type=FailureType.APPLICATION_NOT_FOREGROUND,
            metadata={"app_name": "Notepad"},
        )

        plan = self.engine.plan_recovery(failure)
        assert plan.strategy == RecoveryStrategyType.FOCUS_APPLICATION
        assert plan.can_continue is True
        assert len(plan.actions) == 2
        assert plan.actions[0].action_type == ActionType.FOCUS_APPLICATION
        assert plan.actions[0].target == "Notepad"
        assert plan.actions[1] == act

    def test_recovery_application_not_running_launches(self):
        act = Action(action_type=ActionType.CLICK, target="New")
        failure = FailureInfo(
            action=act,
            failure_type=FailureType.APPLICATION_NOT_RUNNING,
            metadata={"app_name": "Chrome"},
        )

        plan = self.engine.plan_recovery(failure)
        assert plan.strategy == RecoveryStrategyType.GLOBAL_REPLAN
        assert len(plan.actions) == 3
        assert plan.actions[0].action_type == ActionType.LAUNCH_APPLICATION
        assert plan.actions[0].target == "Chrome"

    def test_recovery_exceeded_retries_fails_safely(self):
        act = Action(action_type=ActionType.CLICK, target="Missing")
        failure = FailureInfo(
            action=act,
            failure_type=FailureType.TARGET_NOT_FOUND,
            attempt=5,
        )

        plan = self.engine.plan_recovery(failure)
        assert plan.strategy == RecoveryStrategyType.FAIL_SAFELY
        assert plan.can_continue is False
        assert len(plan.actions) == 0
