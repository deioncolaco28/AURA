"""
app/core/computer_state.py

Canonical representation of the complete computer state for AURA.
Captures structured, multi-dimensional snapshots across:
1. Desktop & Window hierarchy (HWND, titles, classes, bounds, foreground)
2. Process state (PIDs, executables, host PID distinction)
3. UI elements & screen text
4. Browser state (URL, active tab, title)
5. Filesystem state (file existence, modification timestamps, sizes)
6. Application modal/dialog states (Save As dialogs, error alerts)
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WindowInfo:
    """Represents a top-level or child desktop window."""
    hwnd: int = 0
    title: str = ""
    class_name: str = ""
    pid: int = 0
    process_name: str = ""
    is_visible: bool = True
    is_foreground: bool = False
    is_minimized: bool = False
    bounds: tuple[int, int, int, int] | None = None  # (left, top, right, bottom)
    is_dialog: bool = False

    @property
    def is_interactive_gui(self) -> bool:
        """Determines if the window is an actual interactive GUI window rather than a shell/background helper."""
        t_clean = self.title.strip().lower()
        if not t_clean or t_clean in (
            "n/a",
            "program manager",
            "desktop",
            "shell_traywnd",
            "olemainthreadwndname",
            "default ime",
            "msctfime ui",
            "dde server window",
        ):
            return False
        if t_clean.startswith(".net-broadcasteventwindow") or t_clean.startswith("gdi+"):
            return False
        return self.is_visible and not self.is_minimized


@dataclass
class FileSnapshot:
    """Snapshot of a tracked filesystem path."""
    path: str
    exists: bool = False
    is_dir: bool = False
    size_bytes: int = 0
    mtime: float = 0.0
    extension: str = ""


@dataclass
class BrowserSnapshot:
    """Snapshot of browser state."""
    is_open: bool = False
    url: str | None = None
    title: str | None = None
    active_tab_index: int = 0


@dataclass
class ComputerState:
    """
    Complete state snapshot of the computer at a specific point in time.
    Used for before/after comparison and goal verification.
    """
    timestamp: float = field(default_factory=time.time)
    windows: list[WindowInfo] = field(default_factory=list)
    foreground_window: WindowInfo | None = None
    running_processes: list[dict[str, Any]] = field(default_factory=list)
    files: dict[str, FileSnapshot] = field(default_factory=dict)
    browser: BrowserSnapshot = field(default_factory=BrowserSnapshot)
    active_dialogs: list[WindowInfo] = field(default_factory=list)
    screen_text: str = ""
    screen_signature: str | None = None
    host_pid: int = field(default_factory=os.getpid)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def interactive_windows(self) -> list[WindowInfo]:
        """Return only real interactive top-level application windows."""
        return [w for w in self.windows if w.is_interactive_gui]

    def find_windows_by_title(self, query: str) -> list[WindowInfo]:
        """Find interactive windows containing the given query string."""
        q = query.lower()
        return [w for w in self.interactive_windows if q in w.title.lower()]

    def find_windows_by_process(self, process_name: str) -> list[WindowInfo]:
        """Find interactive windows belonging to a given executable/process."""
        p = process_name.lower()
        if not p.endswith(".exe"):
            p_clean = p
        else:
            p_clean = p[:-4]
        return [
            w for w in self.interactive_windows
            if p_clean in w.process_name.lower() or p in w.process_name.lower()
        ]

    def is_app_open(self, app_name: str) -> bool:
        """Check if an interactive window for the app is open."""
        return len(self.find_windows_by_process(app_name)) > 0 or len(self.find_windows_by_title(app_name)) > 0

    def has_file(self, path: str) -> bool:
        """Check if a tracked file exists in the snapshot."""
        norm = os.path.abspath(path).lower()
        for k, v in self.files.items():
            if os.path.abspath(k).lower() == norm and v.exists:
                return True
        return False


class ComputerStateCapturer:
    """
    Efficiently captures ComputerState snapshots on Windows.
    Safely falls back on non-Windows platforms or in mock environments.
    """

    def __init__(self):
        self.host_pid = os.getpid()

    def capture_state(
        self,
        tracked_paths: list[str] | None = None,
        include_screen_text: bool = False,
    ) -> ComputerState:
        """Capture a complete snapshot of current computer state."""
        state = ComputerState(host_pid=self.host_pid)

        # 1. Capture Windows & Processes
        windows, foreground = self._capture_windows()
        state.windows = windows
        state.foreground_window = foreground

        # 2. Identify active dialogs (Save As, Open, MsgBox, Confirm)
        state.active_dialogs = [
            w for w in windows
            if w.is_dialog or any(d in w.title.lower() for d in ("save as", "save file", "open file", "confirm", "warning", "error"))
        ]

        # 3. Capture Tracked Filesystem paths
        if tracked_paths:
            for p in tracked_paths:
                state.files[p] = self._snapshot_file(p)

        # 4. Capture Browser State (if accessible)
        state.browser = self._capture_browser()

        return state

    def _capture_windows(self) -> tuple[list[WindowInfo], WindowInfo | None]:
        """Query top-level desktop windows via EnumWindows or tasklist."""
        windows: list[WindowInfo] = []
        foreground: WindowInfo | None = None

        if sys.platform == "win32":
            try:
                import ctypes
                from ctypes import wintypes

                user32 = ctypes.windll.user32
                kernel32 = ctypes.windll.kernel32

                fg_hwnd = user32.GetForegroundWindow()

                @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
                def enum_proc(hwnd, lparam):
                    if user32.IsWindowVisible(hwnd):
                        length = user32.GetWindowTextLengthW(hwnd)
                        title = ""
                        if length > 0:
                            buf = ctypes.create_unicode_buffer(length + 1)
                            user32.GetWindowTextW(hwnd, buf, length + 1)
                            title = buf.value

                        class_buf = ctypes.create_unicode_buffer(256)
                        user32.GetClassNameW(hwnd, class_buf, 256)
                        cls_name = class_buf.value

                        pid = wintypes.DWORD()
                        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

                        rect = wintypes.RECT()
                        user32.GetWindowRect(hwnd, ctypes.byref(rect))
                        bounds = (rect.left, rect.top, rect.right, rect.bottom)
                        is_fg = (hwnd == fg_hwnd)
                        is_min = bool(user32.IsIconic(hwnd))

                        is_dlg = bool(
                            cls_name == "#32770"  # standard Windows Dialog class
                            or "dialog" in cls_name.lower()
                            or any(k in title.lower() for k in ("save as", "open file", "browse"))
                        )

                        winfo = WindowInfo(
                            hwnd=hwnd,
                            title=title,
                            class_name=cls_name,
                            pid=pid.value,
                            process_name=self._get_process_name_for_pid(pid.value),
                            is_visible=True,
                            is_foreground=is_fg,
                            is_minimized=is_min,
                            bounds=bounds,
                            is_dialog=is_dlg,
                        )
                        windows.append(winfo)
                        if is_fg:
                            nonlocal foreground
                            foreground = winfo
                    return True

                user32.EnumWindows(enum_proc, 0)
                return windows, foreground

            except Exception:
                pass

        # Fallback using applications.py find_process_windows
        from app.automation.applications import find_process_windows
        for exe in ("explorer.exe", "notepad.exe", "chrome.exe", "CalculatorApp.exe", "WindowsTerminal.exe", "powershell.exe", "cmd.exe"):
            for w in find_process_windows(exe):
                winfo = WindowInfo(
                    hwnd=0,
                    title=w.get("window_title", ""),
                    pid=w.get("pid", 0),
                    process_name=w.get("process_name", exe),
                    is_visible=w.get("has_gui_window", True),
                )
                windows.append(winfo)

        return windows, foreground

    def _get_process_name_for_pid(self, pid: int) -> str:
        """Resolve process executable name from PID."""
        if pid <= 0:
            return ""
        try:
            import ctypes
            from ctypes import wintypes
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            kernel32 = ctypes.windll.kernel32
            h_proc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if h_proc:
                try:
                    buf = ctypes.create_unicode_buffer(1024)
                    size = wintypes.DWORD(1024)
                    if hasattr(kernel32, "QueryFullProcessImageNameW"):
                        if kernel32.QueryFullProcessImageNameW(h_proc, 0, buf, ctypes.byref(size)):
                            return os.path.basename(buf.value)
                finally:
                    kernel32.CloseHandle(h_proc)
        except Exception:
            pass
        return ""

    def _snapshot_file(self, path: str) -> FileSnapshot:
        """Create a snapshot of the given file path."""
        try:
            if os.path.exists(path):
                st = os.stat(path)
                return FileSnapshot(
                    path=path,
                    exists=True,
                    is_dir=os.path.isdir(path),
                    size_bytes=st.st_size,
                    mtime=st.st_mtime,
                    extension=os.path.splitext(path)[1].lower(),
                )
        except OSError:
            pass
        return FileSnapshot(
            path=path,
            exists=False,
            extension=os.path.splitext(path)[1].lower() if path else "",
        )

    def _capture_browser(self) -> BrowserSnapshot:
        """Capture active browser URL and state if available."""
        try:
            from app.automation.browser_manager import BrowserManager
            # Check without mutating
            bm = BrowserManager()
            if bm.driver is not None:
                return BrowserSnapshot(
                    is_open=True,
                    url=bm.driver.current_url,
                    title=bm.driver.title,
                )
        except Exception:
            pass
        return BrowserSnapshot(is_open=False)
