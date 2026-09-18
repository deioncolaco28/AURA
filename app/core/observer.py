import time
from abc import ABC, abstractmethod

from app.core.observation import ScreenObservation
from app.perception.ocr import TesseractOCR
from app.perception.perception_manager import (
    PerceptionManager,
)
from app.perception.screenshot import ScreenshotCapture


class ComputerObserver(ABC):
    """
    Abstract interface for observing the current
    computer state.
    """

    @abstractmethod
    def observe(self) -> ScreenObservation:
        raise NotImplementedError


class ScreenObserver(ComputerObserver):
    """
    Development implementation of ComputerObserver.

    Captures the current screen and analyzes it using
    the configured perception pipeline.
    """

    def __init__(
        self,
        screenshot_capture: ScreenshotCapture | None = None,
        perception_manager: PerceptionManager | None = None,
    ):
        self.screenshot_capture = (
            screenshot_capture
            or ScreenshotCapture()
        )

        self.perception_manager = (
            perception_manager
            or PerceptionManager(
                ocr=TesseractOCR()
            )
        )

    def observe(self) -> ScreenObservation:
        """
        Capture and analyze the current screen.

        Populates timestamp, processes, and window_title in addition
        to the existing screen_text, elements, and screenshot fields.
        """

        screenshot = (
            self.screenshot_capture.capture()
        )

        perception = (
            self.perception_manager.analyze(
                screenshot
            )
        )

        screen_text = self._extract_screen_text(
            perception
        )

        processes = self._get_running_processes()
        window_title = self._get_foreground_window()
        foreground_app = self._get_foreground_process()

        dimensions = getattr(screenshot, "size", None) if screenshot is not None else None
        if isinstance(dimensions, tuple) and len(dimensions) == 2:
            screen_dimensions = (int(dimensions[0]), int(dimensions[1]))
        else:
            screen_dimensions = None

        screen_sig = f"{len(perception.elements)}:{len(screen_text)}:{hash(screen_text) & 0xFFFFFFFF:08x}"

        return ScreenObservation(
            screen_text=screen_text,
            elements=list(
                perception.elements
            ),
            screenshot=screenshot,
            timestamp=time.time(),
            processes=processes,
            window_title=window_title,
            foreground_app=foreground_app,
            screen_dimensions=screen_dimensions,
            screen_signature=screen_sig,
            metadata={
                "sources_used": (
                    perception.sources_used
                ),
                "screen_description": (
                    perception.screen_description
                ),
            },
        )

    @staticmethod
    def _extract_screen_text(
        perception,
    ) -> str:
        """
        Combine readable text from perceived UI elements.
        """

        texts = []

        for element in perception.elements:
            if element.text:
                texts.append(
                    element.text.strip()
                )

        return "\n".join(
            text
            for text in texts
            if text
        )

    @staticmethod
    def _get_running_processes() -> list[str]:
        """
        Return a list of running process names.

        Falls back gracefully when psutil is unavailable.
        """

        try:
            import psutil

            return [
                proc.name().lower()
                for proc in psutil.process_iter(["name"])
                if proc.info.get("name")
            ]

        except Exception:
            return []

    @staticmethod
    def _get_foreground_window() -> str | None:
        """
        Return the foreground window title on Windows.

        Falls back gracefully when pygetwindow or ctypes are unavailable.
        """

        try:
            import ctypes

            GetForegroundWindow = ctypes.windll.user32.GetForegroundWindow
            GetWindowTextW = ctypes.windll.user32.GetWindowTextW
            GetWindowTextLengthW = (
                ctypes.windll.user32.GetWindowTextLengthW
            )

            hwnd = GetForegroundWindow()
            length = GetWindowTextLengthW(hwnd)

            if length == 0:
                return None

            buf = ctypes.create_unicode_buffer(length + 1)
            GetWindowTextW(hwnd, buf, length + 1)
            return buf.value or None

        except Exception:
            return None

    @staticmethod
    def _get_foreground_process() -> str | None:
        """
        Return the process name of the foreground window on Windows.
        """
        try:
            import ctypes
            import psutil

            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                return None

            pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(
                hwnd, ctypes.byref(pid)
            )

            if pid.value:
                return psutil.Process(pid.value).name().lower()

            return None
        except Exception:
            return None