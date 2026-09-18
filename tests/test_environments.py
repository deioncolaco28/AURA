"""
Tests for Environment abstraction and EnvironmentRegistry.
"""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from app.automation.environments.environment import Environment, EnvironmentCapability
from app.automation.environments.desktop_environment import DesktopEnvironment
from app.automation.environments.browser_environment import BrowserEnvironment
from app.automation.environments.filesystem_environment import FileSystemEnvironment
from app.automation.environments.application_environment import ApplicationEnvironment
from app.automation.environments.environment_registry import EnvironmentRegistry


class TestEnvironments:
    def test_desktop_environment_capabilities(self):
        mock_dm = MagicMock()
        env = DesktopEnvironment(desktop_manager=mock_dm)
        assert env.name == "desktop"
        assert env.supports(EnvironmentCapability.MOUSE_CLICK)
        assert env.supports(EnvironmentCapability.KEYBOARD_TYPE)
        assert env.supports(EnvironmentCapability.VISUAL_LOCATE)
        assert not env.supports(EnvironmentCapability.FS_READ)

        env.click(100, 200)
        mock_dm.click.assert_called_once_with(x=100, y=200, button="left")

        env.type_text("hello")
        mock_dm.type_text.assert_called_once_with("hello", 0.02)

    def test_browser_environment_capabilities(self):
        mock_bm = MagicMock()
        mock_bm.is_available.return_value = True
        env = BrowserEnvironment(browser_manager=mock_bm)
        assert env.name == "browser"
        assert env.supports(EnvironmentCapability.BROWSER_NAVIGATE)
        assert env.supports(EnvironmentCapability.BROWSER_CLICK)
        assert env.supports(EnvironmentCapability.BROWSER_TAB_OPEN)

        env.navigate("https://example.com")
        mock_bm.navigate.assert_called_once_with("https://example.com")

    def test_filesystem_environment_capabilities(self, tmp_path):
        mock_fm = MagicMock()
        env = FileSystemEnvironment(filesystem_manager=mock_fm)
        assert env.name == "filesystem"
        assert env.supports(EnvironmentCapability.FS_CREATE_FILE)
        assert env.supports(EnvironmentCapability.FS_READ)
        assert env.supports(EnvironmentCapability.FS_DELETE)

        env.create_file("test.txt", "data")
        mock_fm.create_file.assert_called_once_with(path="test.txt", content="data")

    def test_application_environment_capabilities(self):
        mock_am = MagicMock()
        env = ApplicationEnvironment(application_manager=mock_am)
        assert env.name == "application"
        assert env.supports(EnvironmentCapability.APP_LAUNCH)
        assert env.supports(EnvironmentCapability.APP_CLOSE)
        assert env.supports(EnvironmentCapability.APP_FOCUS)

        env.launch("notepad")
        mock_am.launch.assert_called_once_with("notepad", parameters=None)

    def test_environment_registry_lookups(self):
        registry = EnvironmentRegistry()
        assert registry.desktop is not None
        assert registry.browser is not None
        assert registry.filesystem is not None
        assert registry.application is not None

        # Capability lookup
        env_fs = registry.find_environment_for_capability(EnvironmentCapability.FS_SEARCH)
        assert env_fs.name == "filesystem"

        env_br = registry.find_environment_for_capability(EnvironmentCapability.BROWSER_NAVIGATE)
        assert env_br.name == "browser"

        # Action type lookup
        assert registry.find_environment_for_action("OPEN_URL").name == "browser"
        assert registry.find_environment_for_action("CREATE_FOLDER").name == "filesystem"
        assert registry.find_environment_for_action("LAUNCH_APPLICATION").name == "application"
        assert registry.find_environment_for_action("CLICK").name == "desktop"
