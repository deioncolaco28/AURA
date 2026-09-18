"""
app/automation/environments/browser_environment.py

Browser execution environment for web automation and web page interactions.
"""

from __future__ import annotations

from typing import Any
from app.automation.environments.environment import Environment, EnvironmentCapability


class BrowserEnvironment(Environment):
    """
    Execution environment for web browsers (Chrome, Edge, Playwright).
    """

    def __init__(self, browser_manager: Any = None):
        self._browser_manager = browser_manager

    @property
    def name(self) -> str:
        return "browser"

    def supported_capabilities(self) -> set[EnvironmentCapability]:
        return {
            EnvironmentCapability.BROWSER_NAVIGATE,
            EnvironmentCapability.BROWSER_BACK,
            EnvironmentCapability.BROWSER_FORWARD,
            EnvironmentCapability.BROWSER_REFRESH,
            EnvironmentCapability.BROWSER_CLICK,
            EnvironmentCapability.BROWSER_TYPE,
            EnvironmentCapability.BROWSER_SELECT,
            EnvironmentCapability.BROWSER_SUBMIT,
            EnvironmentCapability.BROWSER_SCROLL,
            EnvironmentCapability.BROWSER_TAB_OPEN,
            EnvironmentCapability.BROWSER_TAB_CLOSE,
            EnvironmentCapability.BROWSER_TAB_SWITCH,
            EnvironmentCapability.BROWSER_EXTRACT,
        }

    @property
    def browser_manager(self) -> Any:
        if self._browser_manager is None:
            from app.automation.browser_manager import BrowserManager
            self._browser_manager = BrowserManager()
        return self._browser_manager

    def is_available(self) -> bool:
        return self.browser_manager is not None and self.browser_manager.is_available()

    def navigate(self, url: str) -> Any:
        return self.browser_manager.navigate(url)

    def back(self) -> None:
        self.browser_manager.back()

    def forward(self) -> None:
        self.browser_manager.forward()

    def refresh(self) -> None:
        self.browser_manager.refresh()

    def click(self, target: str) -> None:
        self.browser_manager.click(target)

    def type_text(self, target: str, text: str) -> None:
        self.browser_manager.type_text(target, text)

    def submit(self, target: str | None = None) -> None:
        self.browser_manager.submit(target)

    def scroll(self, delta: int) -> None:
        self.browser_manager.scroll(delta)

    def open_tab(self, url: str | None = None) -> Any:
        return self.browser_manager.open_tab(url)

    def close_tab(self, index: int | None = None) -> None:
        self.browser_manager.close_tab(index)

    def switch_tab(self, index: int) -> None:
        self.browser_manager.switch_tab(index)

    def extract_content(self) -> str:
        return self.browser_manager.extract_content()
