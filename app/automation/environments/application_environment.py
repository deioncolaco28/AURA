"""
app/automation/environments/application_environment.py

Application execution environment for managing desktop applications and windows.
"""

from __future__ import annotations

from typing import Any
from app.automation.environments.environment import Environment, EnvironmentCapability


class ApplicationEnvironment(Environment):
    """
    Execution environment for managing Windows desktop applications and top-level windows.
    """

    def __init__(self, application_manager: Any = None):
        self._application_manager = application_manager

    @property
    def name(self) -> str:
        return "application"

    def supported_capabilities(self) -> set[EnvironmentCapability]:
        return {
            EnvironmentCapability.APP_LAUNCH,
            EnvironmentCapability.APP_CLOSE,
            EnvironmentCapability.APP_FOCUS,
            EnvironmentCapability.APP_MINIMIZE,
            EnvironmentCapability.APP_MAXIMIZE,
            EnvironmentCapability.APP_RESTORE,
            EnvironmentCapability.APP_SWITCH,
            EnvironmentCapability.APP_DETECT,
            EnvironmentCapability.APP_VERIFY_RUNNING,
        }

    @property
    def application_manager(self) -> Any:
        if self._application_manager is None:
            from app.automation.application_manager import ApplicationManager
            self._application_manager = ApplicationManager()
        return self._application_manager

    def launch(self, application: str, parameters: list[str] | None = None) -> Any:
        return self.application_manager.launch(application, parameters=parameters)

    def close(self, application: str) -> bool:
        return self.application_manager.close(application)

    def focus(self, application: str) -> bool:
        return self.application_manager.focus(application)

    def minimize(self, application: str) -> bool:
        return self.application_manager.minimize(application)

    def maximize(self, application: str) -> bool:
        return self.application_manager.maximize(application)

    def restore(self, application: str) -> bool:
        return self.application_manager.restore(application)

    def is_running(self, application: str) -> bool:
        return self.application_manager.is_running(application)

    def is_foreground(self, application: str) -> bool:
        return self.application_manager.is_foreground(application)
