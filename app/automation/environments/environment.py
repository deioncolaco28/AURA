"""
app/automation/environments/environment.py

Base interface and capability definitions for AURA execution environments.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Any, Callable


class EnvironmentCapability(Enum):
    """Capabilities supported by various execution environments."""

    # Desktop
    MOUSE_CLICK = auto()
    MOUSE_DOUBLE_CLICK = auto()
    MOUSE_RIGHT_CLICK = auto()
    MOUSE_MOVE = auto()
    MOUSE_DRAG = auto()
    MOUSE_SCROLL = auto()
    KEYBOARD_TYPE = auto()
    KEYBOARD_PRESS = auto()
    KEYBOARD_HOTKEY = auto()
    VISUAL_LOCATE = auto()

    # Browser
    BROWSER_NAVIGATE = auto()
    BROWSER_BACK = auto()
    BROWSER_FORWARD = auto()
    BROWSER_REFRESH = auto()
    BROWSER_CLICK = auto()
    BROWSER_TYPE = auto()
    BROWSER_SELECT = auto()
    BROWSER_SUBMIT = auto()
    BROWSER_SCROLL = auto()
    BROWSER_TAB_OPEN = auto()
    BROWSER_TAB_CLOSE = auto()
    BROWSER_TAB_SWITCH = auto()
    BROWSER_EXTRACT = auto()

    # FileSystem
    FS_LIST = auto()
    FS_SEARCH = auto()
    FS_CREATE_FILE = auto()
    FS_CREATE_FOLDER = auto()
    FS_READ = auto()
    FS_WRITE = auto()
    FS_OPEN = auto()
    FS_COPY = auto()
    FS_MOVE = auto()
    FS_RENAME = auto()
    FS_DELETE = auto()
    FS_COMPRESS = auto()
    FS_EXTRACT = auto()

    # Application
    APP_LAUNCH = auto()
    APP_CLOSE = auto()
    APP_FOCUS = auto()
    APP_MINIMIZE = auto()
    APP_MAXIMIZE = auto()
    APP_RESTORE = auto()
    APP_SWITCH = auto()
    APP_DETECT = auto()
    APP_VERIFY_RUNNING = auto()

    # Content Intelligence
    CONTENT_EXTRACT = auto()
    CONTENT_SEARCH = auto()
    CONTENT_SUMMARIZE = auto()
    CONTENT_QA = auto()
    CONTENT_CREATE_DOCX = auto()
    CONTENT_CREATE_XLSX = auto()
    CONTENT_CREATE_PPTX = auto()
    CONTENT_ANALYZE_SHEET = auto()


class Environment(ABC):
    """
    Abstract Base Class for an execution environment.
    Exposes capabilities without exposing implementation details to high-level planning.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the environment."""
        raise NotImplementedError

    @abstractmethod
    def supported_capabilities(self) -> set[EnvironmentCapability]:
        """Return the set of capabilities this environment supports."""
        raise NotImplementedError

    def supports(self, capability: EnvironmentCapability) -> bool:
        """Check if this environment supports a specific capability."""
        return capability in self.supported_capabilities()

    def is_available(self) -> bool:
        """Check if this environment is currently active and usable."""
        return True

    def initialize(self) -> None:
        """Optional setup/initialization for the environment."""
        pass

    def cleanup(self) -> None:
        """Optional teardown for the environment."""
        pass
