"""
Tests for StateVerifier and Whole-PC Replanner Recovery scenarios.
"""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from app.core.execution import ExecutionContext
from app.core.failure import FailureInfo, FailureType
from app.core.observation import ScreenObservation
from app.core.rule_based_replanner import RuleBasedReplanner
from app.intelligence.action import Action, ActionType
from app.intelligence.task import Task
from app.verification.state_verifier import StateVerifier, StateVerificationResult


class TestStateVerifierAndRecovery:
    def test_state_verifier_application_running(self):
        verifier = StateVerifier()
        mock_app_verifier = MagicMock()
        mock_app_verifier.is_running.return_value = True
        verifier.application_verifier = mock_app_verifier

        action = Action(
            action_type=ActionType.LAUNCH_APPLICATION,
            target="notepad",
            verification={"type": "APPLICATION_RUNNING", "processes": ["notepad.exe"]},
        )

        res = verifier.verify_action(action)
        assert res.verified is True
        assert res.verification_type == "APPLICATION_RUNNING"

    def test_state_verifier_browser_url(self):
        verifier = StateVerifier()
        mock_bm = MagicMock()
        mock_bm.get_current_url.return_value = "https://www.google.com/search?q=AURA"

        action = Action(
            action_type=ActionType.OPEN_URL,
            target="https://www.google.com",
            verification={"type": "BROWSER_URL", "url": "google.com"},
        )

        res = verifier.verify_action(action, browser_manager=mock_bm)
        assert res.verified is True

    def test_replanner_recovery_application_not_foreground(self):
        replanner = RuleBasedReplanner()
        task = Task(goal="Click Button")
        ctx = ExecutionContext(goal="Click Button", total_steps=1)
        failed_act = Action(action_type=ActionType.CLICK, target="Save")
        obs = ScreenObservation()

        failure = FailureInfo(
            action=failed_act,
            failure_type=FailureType.APPLICATION_NOT_FOREGROUND,
            metadata={"app_name": "Notepad"},
        )

        replanned_actions = replanner.replan(task, ctx, failed_act, obs, failure=failure)
        assert len(replanned_actions) == 2
        assert replanned_actions[0].action_type == ActionType.FOCUS_APPLICATION
        assert replanned_actions[0].target == "Notepad"
        assert replanned_actions[1] == failed_act

    def test_replanner_recovery_application_not_running(self):
        replanner = RuleBasedReplanner()
        task = Task(goal="Click Button")
        ctx = ExecutionContext(goal="Click Button", total_steps=1)
        failed_act = Action(action_type=ActionType.CLICK, target="Save")
        obs = ScreenObservation()

        failure = FailureInfo(
            action=failed_act,
            failure_type=FailureType.APPLICATION_NOT_RUNNING,
            metadata={"app_name": "Chrome"},
        )

        replanned_actions = replanner.replan(task, ctx, failed_act, obs, failure=failure)
        assert len(replanned_actions) == 3
        assert replanned_actions[0].action_type == ActionType.LAUNCH_APPLICATION
        assert replanned_actions[0].target == "Chrome"
        assert replanned_actions[1].action_type == ActionType.WAIT
        assert replanned_actions[2] == failed_act

    def test_replanner_recovery_target_ambiguous(self):
        replanner = RuleBasedReplanner()
        task = Task(goal="Click Edit")
        ctx = ExecutionContext(goal="Click Edit", total_steps=1)
        failed_act = Action(action_type=ActionType.CLICK, target="Edit")
        obs = ScreenObservation()

        failure = FailureInfo(
            action=failed_act,
            failure_type=FailureType.TARGET_AMBIGUOUS,
            metadata={"clarification_question": "Did you mean the top Edit or bottom Edit?"},
        )

        replanned_actions = replanner.replan(task, ctx, failed_act, obs, failure=failure)
        assert len(replanned_actions) == 1
        assert replanned_actions[0].action_type == ActionType.SPEAK
        assert "Did you mean" in replanned_actions[0].value
