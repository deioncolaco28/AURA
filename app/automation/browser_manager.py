"""
app/automation/browser_manager.py

High-level browser manager coordinating DOM operations, visual grounding fallbacks,
tab management, and bounded state verification.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from app.automation.browser import BrowserController, BrowserResult
from app.perception.accessibility import DOMAccessibilityProvider
from app.perception.perception_manager import PerceptionManager
from app.perception.ui_element import UIElement

logger = logging.getLogger(__name__)


class BrowserManager:
    """
    Coordinates browser automation with hybrid DOM + visual perception and state verification.
    """

    def __init__(
        self,
        controller: BrowserController | None = None,
        perception_manager: PerceptionManager | None = None,
    ):
        self.controller = controller or BrowserController()
        self.perception_manager = perception_manager or PerceptionManager()
        self.dom_provider = DOMAccessibilityProvider(browser_controller=self.controller)

    def is_available(self) -> bool:
        return self.controller.is_available()

    def navigate(self, url: str) -> BrowserResult:
        """Navigate to URL and wait for page ready."""
        return self.controller.navigate(url)

    def back(self) -> None:
        self.controller.back()

    def forward(self) -> None:
        self.controller.forward()

    def refresh(self) -> None:
        self.controller.refresh()

    def get_current_url(self) -> str:
        return self.controller.get_url()

    def get_current_title(self) -> str:
        return self.controller.get_title()

    def open_tab(self, url: str | None = None) -> Any:
        return self.controller.open_tab(url)

    def close_tab(self, index: int | None = None) -> None:
        self.controller.close_tab(index)

    def switch_tab(self, index: int) -> None:
        self.controller.switch_tab(index)

    def extract_content(self) -> str:
        return self.controller.extract_content()

    def scroll(self, delta: int) -> None:
        self.controller.scroll(delta)

    def click(self, target: str) -> None:
        """
        Click an element using hybrid DOM first, falling back to visual grounding.
        """
        try:
            self.controller.click(target)
        except Exception as dom_exc:
            logger.debug(f"DOM click failed for '{target}': {dom_exc}. Falling back to visual grounding.")
            from app.automation.desktop_manager import DesktopManager
            dm = DesktopManager(perception_manager=self.perception_manager)
            grounded = dm.locate_and_click(target)
            if not grounded:
                raise RuntimeError(f"Failed to click target '{target}' via both DOM and visual grounding.") from dom_exc

    def type_text(self, target: str, text: str) -> None:
        """
        Type text into an input field using hybrid DOM first, falling back to visual grounding.
        """
        try:
            self.controller.type_text(target, text)
        except Exception as dom_exc:
            logger.debug(f"DOM fill failed for '{target}': {dom_exc}. Falling back to visual grounding.")
            from app.automation.desktop_manager import DesktopManager
            dm = DesktopManager(perception_manager=self.perception_manager)
            grounded = dm.locate_and_click(target)
            if grounded:
                dm.type_text(text)
            else:
                raise RuntimeError(f"Failed to type into target '{target}' via both DOM and visual grounding.") from dom_exc

    def submit(self, target: str | None = None) -> None:
        self.controller.submit(target)

    def wait_for_url_contains(self, fragment: str, timeout_sec: float = 5.0, poll_interval: float = 0.2) -> bool:
        """Bounded polling until the current URL contains the target fragment."""
        start = time.time()
        while time.time() - start < timeout_sec:
            current_url = self.get_current_url()
            if fragment.lower() in current_url.lower():
                return True
            time.sleep(poll_interval)
        return False

    def wait_for_title_contains(self, fragment: str, timeout_sec: float = 5.0, poll_interval: float = 0.2) -> bool:
        """Bounded polling until the page title contains the target fragment."""
        start = time.time()
        while time.time() - start < timeout_sec:
            try:
                title = self.get_current_title()
                if fragment.lower() in title.lower():
                    return True
            except Exception:
                pass
            time.sleep(poll_interval)
        return False
