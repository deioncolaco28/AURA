"""
app/automation/environments/environment_registry.py

Registry and selector for runtime environments.
"""

from __future__ import annotations

from typing import Any
from app.automation.environments.environment import Environment, EnvironmentCapability
from app.automation.environments.desktop_environment import DesktopEnvironment
from app.automation.environments.browser_environment import BrowserEnvironment
from app.automation.environments.filesystem_environment import FileSystemEnvironment
from app.automation.environments.application_environment import ApplicationEnvironment


class EnvironmentRegistry:
    """
    Maintains active environments and provides capability-based lookup.
    """

    def __init__(
        self,
        desktop: DesktopEnvironment | None = None,
        browser: BrowserEnvironment | None = None,
        filesystem: FileSystemEnvironment | None = None,
        application: ApplicationEnvironment | None = None,
    ):
        self._environments: dict[str, Environment] = {}

        self.register(desktop or DesktopEnvironment())
        self.register(browser or BrowserEnvironment())
        self.register(filesystem or FileSystemEnvironment())
        self.register(application or ApplicationEnvironment())

    def register(self, environment: Environment) -> None:
        """Register an environment."""
        self._environments[environment.name] = environment

    def get(self, name: str) -> Environment | None:
        """Get an environment by name."""
        return self._environments.get(name)

    @property
    def desktop(self) -> DesktopEnvironment:
        return self._environments["desktop"]  # type: ignore

    @property
    def browser(self) -> BrowserEnvironment:
        return self._environments["browser"]  # type: ignore

    @property
    def filesystem(self) -> FileSystemEnvironment:
        return self._environments["filesystem"]  # type: ignore

    @property
    def application(self) -> ApplicationEnvironment:
        return self._environments["application"]  # type: ignore

    def find_environment_for_capability(self, capability: EnvironmentCapability) -> Environment | None:
        """Find the first registered environment that supports the given capability."""
        for env in self._environments.values():
            if env.supports(capability) and env.is_available():
                return env
        return None

    def find_environment_for_action(self, action_type: str) -> Environment | None:
        """Map high-level action type to the best suitable environment."""
        act = action_type.upper()
        if act.startswith("BROWSER_") or act in ("OPEN_URL", "OPEN_TAB", "CLOSE_TAB", "SWITCH_TAB", "SUBMIT_FORM", "EXTRACT_PAGE_CONTENT"):
            return self.browser
        if act.startswith("FS_") or act.endswith("_FILE") or act.endswith("_FOLDER") or act in ("LIST_FILES", "SEARCH_FILES", "READ_FILE", "WRITE_FILE", "COMPRESS_FILES", "EXTRACT_ARCHIVE"):
            return self.filesystem
        if act.startswith("APP_") or act in ("LAUNCH_APPLICATION", "FOCUS_APPLICATION", "CLOSE_APPLICATION", "SWITCH_APPLICATION", "MINIMIZE_WINDOW", "MAXIMIZE_WINDOW", "RESTORE_WINDOW"):
            return self.application
        return self.desktop
