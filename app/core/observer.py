"""
app/core/observer.py

Captures and coordinates screen observation using the perception pipeline.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod

from app.core.observation import ScreenObservation
from app.perception.foreground_detector import ForegroundApplicationDetector
from app.perception.ocr import TesseractOCR
from app.perception.perception_manager import (
    PerceptionManager,
)
from app.perception.screenshot import ScreenshotCapture


class ComputerObserver(ABC):
    """
    Abstract interface for observing the current computer state.
    """

    @abstractmethod
    def observe(self) -> ScreenObservation:
        raise NotImplementedError


class ScreenObserver(ComputerObserver):
    """
    Standard implementation of ComputerObserver.

    Captures the current screen and analyzes it using the unified perception pipeline.
    """

    def __init__(
        self,
        screenshot_capture: ScreenshotCapture | None = None,
        perception_manager: PerceptionManager | None = None,
        foreground_detector: ForegroundApplicationDetector | None = None,
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

        self.foreground_detector = (
            foreground_detector
            or ForegroundApplicationDetector()
        )

    def observe(self) -> ScreenObservation:
        """
        Capture and analyze the current screen.
        """
        fg_ctx = self.foreground_detector.get_foreground_context()
        window_title = fg_ctx.window_title if fg_ctx else None
        foreground_app = fg_ctx.app_name if fg_ctx else None

        screenshot = self.screenshot_capture.capture()

        perception = self.perception_manager.analyze(
            screenshot,
            foreground_app=foreground_app,
            window_title=window_title,
        )

        screen_text = self._extract_screen_text(perception)
        processes = self._get_running_processes()

        dimensions = getattr(screenshot, "size", None) if screenshot is not None else None
        if isinstance(dimensions, tuple) and len(dimensions) == 2:
            screen_dimensions = (int(dimensions[0]), int(dimensions[1]))
        else:
            screen_dimensions = None

        screen_sig = f"{len(perception.elements)}:{len(screen_text)}:{hash(screen_text) & 0xFFFFFFFF:08x}"

        return ScreenObservation(
            screen_text=screen_text,
            elements=list(perception.elements),
            screenshot=screenshot,
            timestamp=time.time(),
            processes=processes,
            window_title=window_title,
            foreground_app=foreground_app,
            foreground_context=fg_ctx,
            ui_graph=perception.ui_graph,
            perception_confidence=perception.overall_confidence,
            sources_used=list(perception.sources_used),
            screen_dimensions=screen_dimensions,
            screen_signature=screen_sig,
            metadata={
                "sources_used": perception.sources_used,
                "screen_description": perception.screen_description,
                "metadata": perception.metadata,
            },
        )

    @staticmethod
    def _extract_screen_text(perception) -> str:
        texts = []
        for element in perception.elements:
            if element.text:
                texts.append(element.text.strip())
        return "\n".join(text for text in texts if text)

    @staticmethod
    def _get_running_processes() -> list[str]:
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
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                return None
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            return buff.value
        except Exception:
            return None

    @staticmethod
    def _get_foreground_process() -> str | None:
        try:
            import ctypes
            import psutil
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                return None
            pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            return psutil.Process(pid.value).name().lower()
        except Exception:
            return None