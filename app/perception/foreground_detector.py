"""
app/perception/foreground_detector.py

Foreground application and window context detection.

Distinguishes between background running processes and the active foreground window,
providing rich context to target ranking, verification, and tutoring workflows.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ApplicationContext:
    """Represents the context of a desktop application."""

    app_name: str
    window_title: str = ""
    process_name: str = ""
    is_foreground: bool = True
    bounds: tuple[int, int, int, int] | None = None
    pid: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def matches(self, query: str) -> bool:
        """Check if this application context matches a query name or process."""
        if not query:
            return False
        q = query.strip().lower()
        if q in self.app_name.lower():
            return True
        if q in self.window_title.lower():
            return True
        if self.process_name and q in self.process_name.lower():
            return True
        return False

    @property
    def is_browser(self) -> bool:
        """True if the application appears to be a web browser."""
        browser_keywords = ("chrome", "msedge", "edge", "firefox", "brave", "opera", "safari", "browser")
        combined = f"{self.app_name} {self.window_title} {self.process_name}".lower()
        return any(k in combined for k in browser_keywords)


class ForegroundApplicationDetector:
    """
    Detects the current foreground application and top-level windows.
    """

    def __init__(self, override_context: ApplicationContext | None = None):
        self._override_context = override_context

    def set_override_context(self, context: ApplicationContext | None) -> None:
        """Set an override context for testing."""
        self._override_context = context

    def get_foreground_context(self) -> ApplicationContext:
        """
        Return the ApplicationContext of the current foreground window.
        """
        if self._override_context is not None:
            return self._override_context

        # Windows native detection via ctypes
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()

            if not hwnd:
                return ApplicationContext(
                    app_name="Desktop",
                    window_title="Desktop",
                    process_name="explorer.exe",
                    is_foreground=True,
                )

            # Get Window title
            length = user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value or "Active Window"

            # Get process ID and name
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            proc_name = ""

            try:
                import psutil
                proc = psutil.Process(pid.value)
                proc_name = proc.name()
            except Exception:
                pass

            app_name = self._infer_app_name(title, proc_name)

            return ApplicationContext(
                app_name=app_name,
                window_title=title,
                process_name=proc_name or app_name.lower() + ".exe",
                is_foreground=True,
                pid=pid.value if pid.value else None,
            )

        except Exception:
            return ApplicationContext(
                app_name="Unknown",
                window_title="Active Window",
                process_name="unknown.exe",
                is_foreground=True,
            )

    def is_app_in_foreground(self, target_name: str) -> bool:
        """
        Check whether an application or process is actively in the foreground.
        """
        if not target_name:
            return False

        current = self.get_foreground_context()
        return current.matches(target_name)

    @staticmethod
    def _infer_app_name(window_title: str, process_name: str) -> str:
        """Infer friendly application name from title and process."""
        proc_lower = process_name.lower()
        title_lower = window_title.lower()

        known_map = {
            "notepad.exe": "Notepad",
            "calculatorapp.exe": "Calculator",
            "calculator.exe": "Calculator",
            "chrome.exe": "Google Chrome",
            "msedge.exe": "Microsoft Edge",
            "mspaint.exe": "Paint",
            "explorer.exe": "File Explorer",
        }

        if proc_lower in known_map:
            return known_map[proc_lower]

        for proc_key, name in known_map.items():
            if name.lower() in title_lower:
                return name

        if " - " in window_title:
            return window_title.split(" - ")[-1].strip()

        return process_name.replace(".exe", "").capitalize() if process_name else "Application"
