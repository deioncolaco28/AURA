"""
Tests for ApplicationManager.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from app.automation.application_manager import ApplicationManager, AppRegistryEntry
from app.perception.foreground_detector import ApplicationContext, ForegroundApplicationDetector


class TestApplicationManager:
    def setup_method(self):
        self.mock_detector = MagicMock(spec=ForegroundApplicationDetector)
        self.am = ApplicationManager(foreground_detector=self.mock_detector)

    def test_resolve_application_aliases(self):
        entry_np = self.am.resolve_application("notepad")
        assert entry_np is not None
        assert entry_np.executable == "notepad.exe"

        entry_alias = self.am.resolve_application("note pad")
        assert entry_alias is not None
        assert entry_alias.logical_name == "Notepad"

        entry_calc = self.am.resolve_application("calculator")
        assert entry_calc is not None
        assert "calc.exe" in entry_calc.process_names

        entry_files = self.am.resolve_application("file manager")
        assert entry_files is not None
        assert entry_files.executable == "explorer.exe"

    def test_launch_registered_application(self):
        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_popen.return_value = mock_proc

            proc = self.am.launch("notepad")
            assert proc == mock_proc
            mock_popen.assert_called_once_with(["notepad.exe"], shell=False)

    def test_launch_unknown_unsupported_application(self):
        with pytest.raises(ValueError, match="Unknown or unsupported"):
            self.am.launch("non_existent_app_xyz")

    def test_is_foreground_detection(self):
        # Foreground is Chrome
        self.mock_detector.get_foreground_context.return_value = ApplicationContext(
            app_name="Google Chrome",
            window_title="Google Search - Google Chrome",
            process_name="chrome.exe",
        )

        assert self.am.is_foreground("chrome") is True
        assert self.am.is_foreground("google chrome") is True
        assert self.am.is_foreground("notepad") is False
