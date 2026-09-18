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

    def get_url(self) -> str:
        def _get_url():
            if self.page is None:
                return ""
            return self.page.url
        return self._run_on_browser_thread(_get_url)

    def is_available(self) -> bool:
        if self._closed:
            return False
        return True

    def navigate(self, url: str) -> BrowserResult:
        return self.open_url(url)

    def back(self) -> None:
        def _back():
            if self.page:
                self.page.go_back()
        self._run_on_browser_thread(_back)

    def forward(self) -> None:
        def _forward():
            if self.page:
                self.page.go_forward()
        self._run_on_browser_thread(_forward)

    def refresh(self) -> None:
        def _refresh():
            if self.page:
                self.page.reload()
        self._run_on_browser_thread(_refresh)

    def click(self, target: str) -> None:
        def _click():
            page = self._start_on_worker()
            # Try selector, then text selector
            try:
                page.click(target, timeout=2000)
            except Exception:
                page.click(f"text={target}", timeout=3000)
        self._run_on_browser_thread(_click)

    def type_text(self, target: str, text: str) -> None:
        def _type():
            page = self._start_on_worker()
            try:
                page.fill(target, text, timeout=2000)
            except Exception:
                page.fill(f"text={target}", text, timeout=3000)
        self._run_on_browser_thread(_type)

    def submit(self, target: str | None = None) -> None:
        def _submit():
            page = self._start_on_worker()
            if target:
                try:
                    page.press(target, "Enter")
                except Exception:
                    page.keyboard.press("Enter")
            else:
                page.keyboard.press("Enter")
        self._run_on_browser_thread(_submit)

    def scroll(self, delta: int) -> None:
        def _scroll():
            page = self._start_on_worker()
            page.mouse.wheel(0, delta)
        self._run_on_browser_thread(_scroll)

    def open_tab(self, url: str | None = None) -> Any:
        def _new_tab():
            if self.browser is None:
                self._start_on_worker()
            context = self.browser.contexts[0] if self.browser.contexts else self.browser.new_context()
            new_p = context.new_page()
            self.page = new_p
            if url:
                new_p.goto(url, wait_until="domcontentloaded")
            return new_p
        return self._run_on_browser_thread(_new_tab)

    def close_tab(self, index: int | None = None) -> None:
        def _close_tab():
            if not self.browser or not self.browser.contexts:
                return
            context = self.browser.contexts[0]
            pages = context.pages
            if pages:
                target_page = pages[index] if (index is not None and 0 <= index < len(pages)) else pages[-1]
                target_page.close()
                if context.pages:
                    self.page = context.pages[-1]
                else:
                    self.page = None
        self._run_on_browser_thread(_close_tab)

    def switch_tab(self, index: int) -> None:
        def _switch_tab():
            if not self.browser or not self.browser.contexts:
                return
            context = self.browser.contexts[0]
            pages = context.pages
            if 0 <= index < len(pages):
                self.page = pages[index]
                self.page.bring_to_front()
        self._run_on_browser_thread(_switch_tab)

    def extract_content(self) -> str:
        def _extract():
            if not self.page:
                return ""
            return self.page.inner_text("body")
        return self._run_on_browser_thread(_extract)

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