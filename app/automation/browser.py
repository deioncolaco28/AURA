from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
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
    Synchronous browser controller for AURA.

    Playwright's Sync API cannot safely run directly inside an
    asyncio event loop.

    Therefore AURA owns Playwright inside a dedicated single worker
    thread. All Playwright operations are submitted to that same
    thread so the Playwright objects remain thread-consistent.

    The public API remains synchronous, so existing ActionExecutor
    and execution-engine code does not need to become async.
    """

    def __init__(
        self,
        headless: bool = False,
    ):
        self.headless = headless

        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.page: Page | None = None

        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="aura-playwright",
        )

        self._closed = False

    # ------------------------------------------------------------------
    # INTERNAL WORKER EXECUTION
    # ------------------------------------------------------------------

    def _run_on_browser_thread(
        self,
        function,
    ):
        if self._closed:
            raise RuntimeError(
                "BrowserController has been closed."
            )

        future = self._executor.submit(
            function
        )

        return future.result()

    # ------------------------------------------------------------------
    # PLAYWRIGHT INITIALIZATION
    # ------------------------------------------------------------------

    def _start_on_worker(self) -> Page:

        if self.page is not None:
            return self.page

        self.playwright = (
            sync_playwright().start()
        )

        self.browser = (
            self.playwright.chromium.launch(
                headless=self.headless
            )
        )

        context = (
            self.browser.new_context()
        )

        self.page = context.new_page()

        return self.page

    def start(self) -> Page:
        """
        Start Chromium on the dedicated Playwright thread.
        """

        return self._run_on_browser_thread(
            self._start_on_worker
        )

    # ------------------------------------------------------------------
    # OPEN URL
    # ------------------------------------------------------------------

    def open_url(
        self,
        url: str,
    ) -> BrowserResult:

        if not url or not url.strip():
            raise ValueError(
                "URL cannot be empty."
            )

        normalized_url = url.strip()

        def _open():
            page = self._start_on_worker()

            page.goto(
                normalized_url,
                wait_until="domcontentloaded",
            )

            return BrowserResult(
                success=True,
                message=f"Opened {normalized_url}",
                url=page.url,
            )

        return self._run_on_browser_thread(
            _open
        )

    # ------------------------------------------------------------------
    # PAGE TITLE
    # ------------------------------------------------------------------

    def get_title(self) -> str:

        def _get_title():

            if self.page is None:
                raise RuntimeError(
                    "Browser has not been started."
                )

            return self.page.title()

        return self._run_on_browser_thread(
            _get_title
        )

    # ------------------------------------------------------------------
    # CLOSE
    # ------------------------------------------------------------------

    def close(self) -> None:

        if self._closed:
            return

        def _close():

            if self.browser is not None:
                self.browser.close()

            if self.playwright is not None:
                self.playwright.stop()

            self.page = None
            self.browser = None
            self.playwright = None

        try:
            self._run_on_browser_thread(
                _close
            )

        finally:
            self._closed = True

            self._executor.shutdown(
                wait=True
            )