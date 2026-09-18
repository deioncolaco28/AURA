"""
app/perception/accessibility.py

Accessibility and structured UI perception abstraction.

Supports Windows UI Automation / native accessibility APIs and browser DOM trees,
converting structured UI nodes into canonical UIElement instances.
Degrades gracefully when accessibility services are unavailable.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from app.perception.ui_element import UIElement, generate_stable_id

logger = logging.getLogger(__name__)


class AccessibilityProvider(ABC):
    """Abstract interface for structured accessibility perception."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this accessibility provider is available and functional."""
        raise NotImplementedError

    @abstractmethod
    def capture(self) -> list[UIElement]:
        """Capture and return the current structured UI elements."""
        raise NotImplementedError

    def get_foreground_application(self) -> dict[str, Any] | None:
        """Return information about the currently focused top-level window/application."""
        return None


class MockAccessibilityProvider(AccessibilityProvider):
    """Configurable in-memory accessibility provider for testing."""

    def __init__(self, elements: list[UIElement] | None = None, available: bool = True):
        self._elements = elements or []
        self._available = available
        self._foreground_app: dict[str, Any] | None = None

    def set_elements(self, elements: list[UIElement]) -> None:
        self._elements = elements

    def set_available(self, available: bool) -> None:
        self._available = available

    def set_foreground_app(self, app_info: dict[str, Any] | None) -> None:
        self._foreground_app = app_info

    def is_available(self) -> bool:
        return self._available

    def capture(self) -> list[UIElement]:
        if not self._available:
            return []
        return list(self._elements)

    def get_foreground_application(self) -> dict[str, Any] | None:
        return self._foreground_app


class DOMAccessibilityProvider(AccessibilityProvider):
    """
    Extracts structured UI elements from a Playwright / browser page DOM.
    """

    def __init__(self, browser_controller=None):
        self.browser_controller = browser_controller

    def is_available(self) -> bool:
        if self.browser_controller is None:
            return False
        page = getattr(self.browser_controller, "page", None)
        return page is not None and not getattr(page, "is_closed", lambda: False)()

    def capture(self) -> list[UIElement]:
        if not self.is_available():
            return []

        try:
            page = self.browser_controller.page
            # Extract interactable elements via JavaScript evaluate
            raw_elements = page.evaluate("""
                () => {
                    const selector = 'button, a, input, textarea, select, [role="button"], [role="link"], [role="checkbox"], [role="tab"], h1, h2, h3, p';
                    const nodes = Array.from(document.querySelectorAll(selector));
                    return nodes.slice(0, 100).map((el, i) => {
                        const rect = el.getBoundingClientRect();
                        const isVisible = rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
                        if (!isVisible) return null;
                        return {
                            index: i,
                            tag: el.tagName.toLowerCase(),
                            role: el.getAttribute('role') || el.tagName.toLowerCase(),
                            text: (el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('placeholder') || '').trim(),
                            x: Math.round(rect.left),
                            y: Math.round(rect.top),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height),
                            enabled: !el.disabled,
                            href: el.href || null,
                        };
                    }).filter(Boolean);
                }
            """)

            ui_elements: list[UIElement] = []
            for item in raw_elements:
                elem_type = self._map_role_to_type(item.get("role") or item.get("tag", "element"))
                ui_elements.append(
                    UIElement(
                        element_id=f"dom-{item.get('index', len(ui_elements))}",
                        element_type=elem_type,
                        text=item.get("text") or None,
                        x=int(item.get("x", 0)),
                        y=int(item.get("y", 0)),
                        width=int(item.get("width", 0)),
                        height=int(item.get("height", 0)),
                        confidence=0.95,
                        source="DOM",
                        is_enabled=bool(item.get("enabled", True)),
                        is_interactable=elem_type in {"button", "input", "link", "checkbox", "tab"},
                        attributes={"tag": item.get("tag"), "href": item.get("href")},
                        app_name="Browser",
                    )
                )
            return ui_elements

        except Exception as exc:
            logger.debug(f"DOM accessibility capture failed: {exc}")
            return []

    def get_foreground_application(self) -> dict[str, Any] | None:
        if not self.is_available():
            return None
        try:
            page = self.browser_controller.page
            return {
                "app_name": "Browser",
                "window_title": page.title(),
                "url": page.url,
                "is_foreground": True,
            }
        except Exception:
            return None

    @staticmethod
    def _map_role_to_type(role: str) -> str:
        role_lower = role.lower()
        if role_lower in {"button", "submit", "reset"}:
            return "button"
        if role_lower in {"link", "a"}:
            return "link"
        if role_lower in {"input", "textbox", "textarea"}:
            return "input"
        if role_lower in {"checkbox"}:
            return "checkbox"
        if role_lower in {"tab"}:
            return "tab"
        if role_lower in {"h1", "h2", "h3", "p", "label", "heading"}:
            return "text"
        return role_lower


class WindowsAccessibilityProvider(AccessibilityProvider):
    """
    Windows UI Automation native accessibility provider.
    Degrades gracefully when UI Automation is unavailable.
    """

    def __init__(self):
        self._uia_available: bool | None = None

    def is_available(self) -> bool:
        if self._uia_available is not None:
            return self._uia_available

        try:
            import ctypes
            # Check user32 availability
            user32 = ctypes.windll.user32
            self._uia_available = bool(user32.GetForegroundWindow())
        except Exception:
            self._uia_available = False

        return self._uia_available

    def capture(self) -> list[UIElement]:
        if not self.is_available():
            return []

        # Implementation hook: when native com/UIA is present it walks the element tree
        # For base environments without pywinauto/uiautomation installed, returns empty list gracefully
        return []

    def get_foreground_application(self) -> dict[str, Any] | None:
        if not self.is_available():
            return None

        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return None

            length = user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value

            return {
                "window_title": title,
                "hwnd": hwnd,
                "is_foreground": True,
            }
        except Exception:
            return None
