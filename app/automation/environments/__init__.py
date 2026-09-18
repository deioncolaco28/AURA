"""
app/automation/environments package
"""

from app.automation.environments.environment import Environment, EnvironmentCapability
from app.automation.environments.desktop_environment import DesktopEnvironment
from app.automation.environments.browser_environment import BrowserEnvironment
from app.automation.environments.filesystem_environment import FileSystemEnvironment
from app.automation.environments.application_environment import ApplicationEnvironment
from app.automation.environments.content_environment import ContentEnvironment
from app.automation.environments.environment_registry import EnvironmentRegistry

__all__ = [
    "Environment",
    "EnvironmentCapability",
    "DesktopEnvironment",
    "BrowserEnvironment",
    "FileSystemEnvironment",
    "ApplicationEnvironment",
    "ContentEnvironment",
    "EnvironmentRegistry",
]
