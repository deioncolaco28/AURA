"""
Tests for FailureClassifier and FailureType classification.
"""

from __future__ import annotations

import pytest

from app.core.failure import FailureClassifier, FailureInfo, FailureType
from app.intelligence.action import Action, ActionType


class TestFailureClassifier:
    def setup_method(self):
        self.classifier = FailureClassifier()
        self.action = Action(action_type=ActionType.CLICK, target="Submit")

    def test_classify_target_ambiguous(self):
        info = self.classifier.classify(self.action, error="Target is ambiguous: found multiple 'Submit' buttons.")
        assert info.failure_type == FailureType.TARGET_AMBIGUOUS
        assert info.recoverability is False

    def test_classify_permission_required(self):
        info = self.classifier.classify(self.action, error="Access denied: Permission required to modify system folder.")
        assert info.failure_type == FailureType.PERMISSION_REQUIRED
        assert info.recoverability is False

    def test_classify_application_not_running(self):
        info = self.classifier.classify(self.action, error="Process 'notepad.exe' is not running.")
        assert info.failure_type == FailureType.APPLICATION_NOT_RUNNING
        assert info.recoverability is True

    def test_classify_application_not_foreground(self):
        info = self.classifier.classify(self.action, error="Application 'Chrome' is not in the foreground.")
        assert info.failure_type == FailureType.APPLICATION_NOT_FOREGROUND
        assert info.recoverability is True

    def test_classify_target_not_found(self):
        info = self.classifier.classify(self.action, error="Target not found on screen.")
        assert info.failure_type == FailureType.TARGET_NOT_FOUND
        assert info.recoverability is True

    def test_classify_timeout(self):
        info = self.classifier.classify(self.action, error="Operation timed out after 5000ms.")
        assert info.failure_type == FailureType.TIMEOUT

    def test_classify_filesystem_error(self):
        info = self.classifier.classify(self.action, error="Filesystem error: No such file or directory.")
        assert info.failure_type == FailureType.FILESYSTEM_ERROR
