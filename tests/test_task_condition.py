"""
Tests for TaskCondition and conditional branch evaluation.
"""

from __future__ import annotations

import pytest

from app.core.observation import ScreenObservation
from app.intelligence.task_condition import ConditionType, TaskCondition


class TestTaskCondition:
    def test_condition_app_is_open(self):
        cond = TaskCondition(condition_type=ConditionType.APP_IS_OPEN, target="chrome.exe")
        obs_open = ScreenObservation(processes=["chrome.exe", "svchost.exe"])
        assert cond.evaluate(observation=obs_open) is True

        obs_closed = ScreenObservation(processes=["notepad.exe"])
        assert cond.evaluate(observation=obs_closed) is False

    def test_condition_folder_and_file_exists(self, tmp_path):
        folder = tmp_path / "Projects"
        folder.mkdir()
        file_path = folder / "test.txt"
        file_path.write_text("content")

        cond_folder = TaskCondition(condition_type=ConditionType.FOLDER_EXISTS, target=str(folder))
        assert cond_folder.evaluate() is True

        cond_file = TaskCondition(condition_type=ConditionType.FILE_EXISTS, target=str(file_path))
        assert cond_file.evaluate() is True

        cond_nonexistent = TaskCondition(condition_type=ConditionType.FILE_EXISTS, target=str(tmp_path / "nope.txt"))
        assert cond_nonexistent.evaluate() is False

    def test_condition_url_matches(self):
        cond = TaskCondition(condition_type=ConditionType.URL_MATCHES, target="google.com")
        obs = ScreenObservation(url="https://www.google.com/search?q=test")
        assert cond.evaluate(observation=obs) is True
