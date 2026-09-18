"""
Tests for ExpectedState and StateComparator.
"""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from app.core.observation import ScreenObservation
from app.core.observation_diff import ObservationDiff
from app.intelligence.expected_state import ExpectedState, StateComparator


class TestExpectedState:
    def test_comparator_application_running(self):
        comparator = StateComparator()
        expected = ExpectedState(app_running="notepad.exe")

        obs_success = ScreenObservation(processes=["notepad.exe", "explorer.exe"])
        res_success = comparator.compare(expected, observation=obs_success)
        assert res_success.success is True
        assert "app_running:notepad.exe" in res_success.matched_conditions

        obs_fail = ScreenObservation(processes=["chrome.exe"])
        res_fail = comparator.compare(expected, observation=obs_fail)
        assert res_fail.success is False
        assert "app_running:notepad.exe" in res_fail.failed_conditions

    def test_comparator_browser_url(self):
        comparator = StateComparator()
        expected = ExpectedState(browser_url_contains="google.com/search")

        obs = ScreenObservation(url="https://www.google.com/search?q=AURA")
        res = comparator.compare(expected, observation=obs)
        assert res.success is True

    def test_comparator_filesystem_and_ui(self, tmp_path):
        test_file = tmp_path / "created.txt"
        test_file.write_text("hello world")

        comparator = StateComparator()
        expected = ExpectedState(
            file_exists=str(test_file),
            text_visible="hello",
        )

        obs = ScreenObservation(screen_text="System active: hello user")
        res = comparator.compare(expected, observation=obs)
        assert res.success is True
        assert len(res.matched_conditions) == 2

    def test_comparator_diff_screen_changed(self):
        comparator = StateComparator()
        expected = ExpectedState(screen_changed=True)

        diff = ObservationDiff(added_text=["Save Completed"])
        res = comparator.compare(expected, diff=diff)
        assert res.success is True
