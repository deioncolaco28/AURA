from __future__ import annotations

from dataclasses import dataclass

from playwright.sync_api import (
    Browser,
    Page,
    Playwright,
    sync_playwright,
)


@dataclass
class BrowserResult:
    success: bool
    message: str = ""
    url: str = ""


class BrowserController:
    """
    Lightweight browser controller for AURA.

    Browser interaction is isolated from desktop automation so that
    Playwright can be used for web-specific tasks while the existing
    PyAutoGUI-based automation continues handling desktop applications.
    """

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.page: Page | None = None

    def start(self) -> Page:
        if self.page is not None:
            return self.page

        self.playwright = sync_playwright().start()

        self.browser = self.playwright.chromium.launch(
            headless=self.headless
        )

        context = self.browser.new_context()

        self.page = context.new_page()

        return self.page

    def open_url(self, url: str) -> BrowserResult:
        if not url or not url.strip():
            raise ValueError("URL cannot be empty.")

        page = self.start()

        page.goto(
            url.strip(),
            wait_until="domcontentloaded",
        )

        return BrowserResult(
            success=True,
            message=f"Opened {url.strip()}",
            url=page.url,
        )

    def get_title(self) -> str:
        if self.page is None:
            raise RuntimeError("Browser has not been started.")

        return self.page.title()

    def close(self) -> None:
        if self.browser is not None:
            self.browser.close()

        if self.playwright is not None:
            self.playwright.stop()

        self.page = None
        self.browser = None
        self.playwright = None