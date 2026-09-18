"""
Tests for tutoring verification logic.

Validates the key behavioral rules from the spec:
- Target existence alone NEVER completes a click instruction.
- SCREEN_CHANGED alone NEVER verifies an action.
- TYPE_TEXT text already present before instruction → NOT COMPLETE.
- TYPE_TEXT text added after instruction → SUCCESS.
- User doing nothing → instruction remains incomplete.
- Delayed user action → eventually succeeds.
- Timeout → returns False (recovery expected).
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from app.core.observation import ScreenObservation
from app.core.observation_diff import ObservationDiff, ObservationDiffer
from app.intelligence.action import ActionType
from app.perception.ui_element import UIElement
from app.tutoring.tutoring_controller import TutoringController
from app.tutoring.instruction import TutoringInstruction


def make_element(eid, text, x=100, y=100, width=100, height=30):
    return UIElement(
        element_id=eid,
        element_type="button",
        text=text,
        x=x, y=y, width=width, height=height,
    )


def make_obs(texts=None, processes=None, window_title=None):
    elements = []
    screen_text = ""
    if texts:
        for i, t in enumerate(texts):
            elements.append(make_element(str(i), t))
        screen_text = "\n".join(texts)
    return ScreenObservation(
        screen_text=screen_text,
        elements=elements,
        processes=list(processes or []),
        window_title=window_title,
    )


def make_controller(observations: list[ScreenObservation]) -> TutoringController:
    """
    Create a TutoringController that serves observations in sequence.
    Later calls return the last observation.
    """
    call_count = [0]

    def fake_observe():
        idx = min(call_count[0], len(observations) - 1)
        call_count[0] += 1
        return observations[idx]

    mock_observer = MagicMock()
    mock_observer.observe.side_effect = fake_observe

    engine = MagicMock()
    engine.describe_target.return_value = "Notepad"
    engine.screenshot_capture = None
    engine.ocr = None

    ctrl = TutoringController(
        observer=mock_observer,
        tutoring_engine=engine,
        poll_interval=0.0,   # no actual sleep in tests
        step_timeout=0.5,
    )

    return ctrl


# ---------------------------------------------------------------------------
# User does nothing — target still visible
# ---------------------------------------------------------------------------


class TestUserDoesNothing:

    def test_click_target_still_visible_not_complete(self):
        """
        Notepad exists before AND after → not complete.
        Target existence alone MUST NOT count as completion.
        """
        baseline = make_obs(["Notepad"])
        after_same = make_obs(["Notepad"])  # nothing changed

        # Serve: baseline, then many identical copies (user never acts).
        obs_sequence = [baseline] + [after_same] * 10
        ctrl = make_controller(obs_sequence)

        instruction = TutoringInstruction(
            message="Click Notepad.",
            target="Notepad",
            action_type=ActionType.CLICK,
            completion={"target_disappears": "Notepad"},
            expected_transition={"target_disappears": "Notepad"},
        )

        success = ctrl._run_single_instruction(instruction)

        assert not success, (
            "Target still visible but user did nothing — must NOT be complete"
        )

    def test_click_completion_requires_state_change(self):
        """No process change, no target disappearance → not complete."""
        baseline = make_obs(processes=["explorer.exe"])
        # After: same processes, same screen.
        after = make_obs(processes=["explorer.exe"])

        ctrl = make_controller([baseline] + [after] * 10)

        instruction = TutoringInstruction(
            message="Click Notepad.",
            target="Notepad",
            action_type=ActionType.CLICK,
            completion={
                "type": "APPLICATION_RUNNING",
                "process": "notepad.exe",
            },
            expected_transition={
                "process_starts": "notepad.exe",
            },
        )

        success = ctrl._run_single_instruction(instruction)
        assert not success


# ---------------------------------------------------------------------------
# Successful click verification
# ---------------------------------------------------------------------------


class TestClickSuccess:

    def test_process_starts_counts_as_click_success(self):
        """
        Before: Notepad in search results.
        After: notepad.exe process started.
        → SUCCESS.
        """
        baseline = make_obs(["Notepad"], processes=["explorer.exe"])
        after_click = make_obs(
            ["Notepad - Untitled"],
            processes=["explorer.exe", "notepad.exe"],
        )

        ctrl = make_controller([baseline, after_click])

        instruction = TutoringInstruction(
            message="Click Notepad.",
            target="Notepad",
            action_type=ActionType.CLICK,
            completion={
                "type": "APPLICATION_RUNNING",
                "process": "notepad.exe",
            },
            expected_transition={
                "process_starts": "notepad.exe",
            },
        )

        success = ctrl._run_single_instruction(instruction)
        assert success

    def test_target_disappears_counts_as_click_success(self):
        """
        Before: Notepad visible.
        After: Notepad disappeared.
        → SUCCESS.
        """
        baseline = make_obs(["Notepad", "Calculator"])
        after_click = make_obs(["Calculator"])  # Notepad gone

        ctrl = make_controller([baseline, after_click])

        instruction = TutoringInstruction(
            message="Click Notepad.",
            target="Notepad",
            action_type=ActionType.CLICK,
            completion={"target_disappears": "Notepad"},
            expected_transition={"target_disappears": "Notepad"},
        )

        success = ctrl._run_single_instruction(instruction)
        assert success


# ---------------------------------------------------------------------------
# Failed click — target still exists, no expected state
# ---------------------------------------------------------------------------


class TestClickFailure:

    def test_notepad_still_exists_no_process_not_complete(self):
        """
        Before: Notepad search result exists.
        After: Notepad still exists, notepad.exe NOT started.
        → NOT COMPLETE.
        """
        baseline = make_obs(["Notepad"], processes=["explorer.exe"])
        after = make_obs(["Notepad"], processes=["explorer.exe"])  # unchanged

        ctrl = make_controller([baseline] + [after] * 10)

        instruction = TutoringInstruction(
            message="Click Notepad.",
            target="Notepad",
            action_type=ActionType.CLICK,
            completion={
                "type": "APPLICATION_RUNNING",
                "process": "notepad.exe",
            },
            expected_transition={
                "process_starts": "notepad.exe",
            },
        )

        success = ctrl._run_single_instruction(instruction)
        assert not success


# ---------------------------------------------------------------------------
# TYPE_TEXT false positive prevention
# ---------------------------------------------------------------------------


class TestTypeTextVerification:

    def test_text_already_present_before_not_complete(self):
        """
        TYPE_TEXT instruction: "Hello World"
        'Hello World' was already on screen BEFORE the instruction.
        User does nothing.
        → NOT COMPLETE.
        """
        baseline = make_obs(["Hello World", "other text"])
        after_same = make_obs(["Hello World", "other text"])  # unchanged

        ctrl = make_controller([baseline] + [after_same] * 10)

        instruction = TutoringInstruction(
            message="Type 'Hello World' into the search field.",
            action_type=ActionType.TYPE_TEXT,
            parameters={"text": "Hello World"},
            completion={"screen_contains": "Hello World"},
            expected_transition={
                "text_appears": "Hello World",
                "requires_baseline": True,
            },
        )

        success = ctrl._run_single_instruction(instruction)
        # The text was there before → must NOT count as user typed it.
        assert not success

    def test_text_added_after_baseline_is_success(self):
        """
        TYPE_TEXT instruction: "Notepad"
        'Notepad' was NOT on screen before.
        User types it → it appears.
        → SUCCESS.
        """
        baseline = make_obs([""])
        after_type = make_obs(["Notepad"])  # text appeared

        ctrl = make_controller([baseline, after_type])

        instruction = TutoringInstruction(
            message="Type 'Notepad' into the search field.",
            action_type=ActionType.TYPE_TEXT,
            parameters={"text": "Notepad"},
            completion={"screen_contains": "Notepad"},
            expected_transition={
                "text_appears": "Notepad",
                "requires_baseline": True,
            },
        )

        success = ctrl._run_single_instruction(instruction)
        assert success


# ---------------------------------------------------------------------------
# SCREEN_CHANGED false positive
# ---------------------------------------------------------------------------


class TestScreenChangedFalsePositive:

    def test_unrelated_screen_change_not_sufficient(self):
        """
        User presses Windows key.
        Screen changes slightly (unrelated clock update).
        Expected: Start menu OR meaningful elements — NOT present.
        → NOT COMPLETE (weak evidence only).
        """
        baseline = make_obs(["Clock: 12:00"])
        # Minimal change: only clock text updated — 1 token difference.
        after = make_obs(["Clock: 12:01"])

        ctrl = make_controller([baseline] + [after] * 10)

        instruction = TutoringInstruction(
            message="Press the Windows key.",
            action_type=ActionType.PRESS_KEY,
            parameters={"key": "win"},
            completion={"screen_changed": True},
            expected_transition={"screen_changed": True},
        )

        # The controller requires MORE than just one token change.
        # Our _verify_press_key requires >= 2 added_elements or 2 added_text,
        # or process change, or window title change.
        success = ctrl._run_single_instruction(instruction)
        assert not success

    def test_meaningful_screen_change_is_accepted(self):
        """
        Many new elements appear (Start menu) → accepted.
        """
        baseline = make_obs(["Taskbar"])
        after = make_obs([
            "Taskbar", "Search Windows", "Pinned", "All apps",
            "Calculator", "Notepad", "Settings"
        ])

        ctrl = make_controller([baseline, after])

        instruction = TutoringInstruction(
            message="Press the Windows key.",
            action_type=ActionType.PRESS_KEY,
            parameters={"key": "win"},
            completion={"screen_changed": True},
            expected_transition={"screen_changed": True},
        )

        success = ctrl._run_single_instruction(instruction)
        assert success


# ---------------------------------------------------------------------------
# Delayed user action
# ---------------------------------------------------------------------------


class TestDelayedUserAction:

    def test_user_acts_after_delay_eventually_succeeds(self):
        """
        User takes a few polling cycles before acting.
        AURA should continue observing and eventually succeed.
        """
        baseline = make_obs(["Notepad"], processes=["explorer.exe"])
        no_change = make_obs(["Notepad"], processes=["explorer.exe"])
        success_obs = make_obs(
            ["Notepad - Untitled"],
            processes=["explorer.exe", "notepad.exe"],
        )

        # 3 "no change" observations, then success.
        ctrl = make_controller(
            [baseline, no_change, no_change, no_change, success_obs]
        )

        instruction = TutoringInstruction(
            message="Click Notepad.",
            target="Notepad",
            action_type=ActionType.CLICK,
            completion={
                "type": "APPLICATION_RUNNING",
                "process": "notepad.exe",
            },
            expected_transition={"process_starts": "notepad.exe"},
        )

        success = ctrl._run_single_instruction(instruction)
        assert success


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------


class TestTimeout:

    def test_user_never_acts_triggers_recovery(self):
        """
        User never acts within the timeout.
        Controller returns False so recovery can be triggered.
        """
        baseline = make_obs(["Notepad"], processes=["explorer.exe"])
        no_change = make_obs(["Notepad"], processes=["explorer.exe"])

        ctrl = make_controller([baseline] + [no_change] * 50)
        ctrl.step_timeout = 0.1  # very short timeout for test

        instruction = TutoringInstruction(
            message="Click Notepad.",
            target="Notepad",
            action_type=ActionType.CLICK,
            completion={"target_disappears": "Notepad"},
            expected_transition={"target_disappears": "Notepad"},
            recovery={"max_attempts": 0},  # no recovery, just fail fast
        )

        success = ctrl._run_single_instruction(instruction)
        assert not success


# ---------------------------------------------------------------------------
# ObservationDiff integration in controller
# ---------------------------------------------------------------------------


class TestObservationDiffInController:

    def test_differ_compares_before_and_after(self):
        """Direct test of _is_verified with a known before/after pair."""
        ctrl = make_controller([])

        before = make_obs(["Notepad"], processes=["explorer.exe"])
        after = make_obs(
            ["Notepad - Untitled"],
            processes=["explorer.exe", "notepad.exe"],
        )

        result = ctrl._is_verified(
            action_type=ActionType.CLICK,
            target="Notepad",
            completion={"type": "APPLICATION_RUNNING", "process": "notepad.exe"},
            expected_transition={"process_starts": "notepad.exe"},
            parameters={},
            before=before,
            after=after,
        )

        assert result

    def test_type_text_requires_text_to_be_added(self):
        """TYPE_TEXT: text already present → NOT complete."""
        ctrl = make_controller([])

        before = make_obs(["Hello World"])  # text already there
        after = make_obs(["Hello World"])   # no change

        result = ctrl._is_verified(
            action_type=ActionType.TYPE_TEXT,
            target=None,
            completion={"screen_contains": "Hello World"},
            expected_transition={"text_appears": "Hello World"},
            parameters={"text": "Hello World"},
            before=before,
            after=after,
        )

        assert not result

    def test_type_text_newly_added_text_completes(self):
        """TYPE_TEXT: text appears after → complete."""
        ctrl = make_controller([])

        before = make_obs([""])
        after = make_obs(["Hello World"])

        result = ctrl._is_verified(
            action_type=ActionType.TYPE_TEXT,
            target=None,
            completion={"screen_contains": "Hello World"},
            expected_transition={"text_appears": "Hello World"},
            parameters={"text": "Hello World"},
            before=before,
            after=after,
        )

        assert result
