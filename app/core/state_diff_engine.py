"""
app/core/state_diff_engine.py

Calculates rich, multi-dimensional state transitions between two ComputerState snapshots.
Provides semantic difference analysis across Windows, Processes, Filesystem, Browser, and Dialogs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.computer_state import ComputerState, WindowInfo, FileSnapshot


@dataclass
class ComputerStateDiff:
    """
    Structured diff between two ComputerState snapshots.
    """
    # Windows
    windows_opened: list[WindowInfo] = field(default_factory=list)
    windows_closed: list[WindowInfo] = field(default_factory=list)
    foreground_changed: bool = False
    foreground_window_before: WindowInfo | None = None
    foreground_window_after: WindowInfo | None = None

    # Processes
    processes_started: list[dict[str, Any]] = field(default_factory=list)
    processes_stopped: list[dict[str, Any]] = field(default_factory=list)

    # Filesystem
    files_created: list[FileSnapshot] = field(default_factory=list)
    files_modified: list[FileSnapshot] = field(default_factory=list)
    files_deleted: list[FileSnapshot] = field(default_factory=list)

    # Dialogs
    dialogs_opened: list[WindowInfo] = field(default_factory=list)
    dialogs_closed: list[WindowInfo] = field(default_factory=list)

    # Browser
    browser_navigated: bool = False
    browser_url_before: str | None = None
    browser_url_after: str | None = None

    # Text & Metadata
    screen_changed: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def has_any_change(self) -> bool:
        """Return True if any measurable environment change occurred."""
        return bool(
            self.windows_opened
            or self.windows_closed
            or self.foreground_changed
            or self.processes_started
            or self.processes_stopped
            or self.files_created
            or self.files_modified
            or self.files_deleted
            or self.dialogs_opened
            or self.dialogs_closed
            or self.browser_navigated
            or self.screen_changed
        )

    def is_app_opened(self, app_name: str) -> bool:
        """Check if an interactive window for the specified app was opened."""
        clean = app_name.lower().replace(".exe", "")
        for w in self.windows_opened:
            if clean in w.process_name.lower() or clean in w.title.lower():
                return True
        return False

    def is_file_created(self, filename_or_path: str) -> bool:
        """Check if a file with the given name or path was created."""
        target = filename_or_path.lower().replace("\\", "/")
        for f in self.files_created:
            norm = f.path.lower().replace("\\", "/")
            if norm.endswith(target) or norm == target:
                return True
        return False


class StateDiffEngine:
    """
    Computes semantic differences between before and after ComputerState snapshots.
    """

    def compute_diff(
        self,
        before: ComputerState | None,
        after: ComputerState | None,
    ) -> ComputerStateDiff:
        """Compute structured difference."""
        if before is None and after is None:
            return ComputerStateDiff()
        if before is None:
            before = ComputerState()
        if after is None:
            after = ComputerState()

        diff = ComputerStateDiff()

        # 1. Window Diffs
        before_hwnds = {w.hwnd: w for w in before.windows if w.hwnd != 0}
        after_hwnds = {w.hwnd: w for w in after.windows if w.hwnd != 0}

        if before_hwnds or after_hwnds:
            diff.windows_opened = [w for hwnd, w in after_hwnds.items() if hwnd not in before_hwnds and w.is_interactive_gui]
            diff.windows_closed = [w for hwnd, w in before_hwnds.items() if hwnd not in after_hwnds and w.is_interactive_gui]
        else:
            # Fallback by title / process if HWNDs are 0 (e.g. tasklist mode)
            before_keys = {(w.process_name.lower(), w.title.strip().lower()) for w in before.interactive_windows}
            diff.windows_opened = [
                w for w in after.interactive_windows
                if (w.process_name.lower(), w.title.strip().lower()) not in before_keys
            ]

        # 2. Foreground Window Diff
        diff.foreground_window_before = before.foreground_window
        diff.foreground_window_after = after.foreground_window
        if before.foreground_window and after.foreground_window:
            if before.foreground_window.hwnd != after.foreground_window.hwnd or before.foreground_window.title != after.foreground_window.title:
                diff.foreground_changed = True
        elif (before.foreground_window is None) != (after.foreground_window is None):
            diff.foreground_changed = True

        # 3. Dialog Diffs
        before_dlgs = {w.hwnd or w.title: w for w in before.active_dialogs}
        after_dlgs = {w.hwnd or w.title: w for w in after.active_dialogs}
        diff.dialogs_opened = [w for k, w in after_dlgs.items() if k not in before_dlgs]
        diff.dialogs_closed = [w for k, w in before_dlgs.items() if k not in after_dlgs]

        # 4. Filesystem Diffs
        for path, after_snap in after.files.items():
            before_snap = before.files.get(path)
            if after_snap.exists:
                if not before_snap or not before_snap.exists:
                    diff.files_created.append(after_snap)
                elif after_snap.mtime > before_snap.mtime or after_snap.size_bytes != before_snap.size_bytes:
                    diff.files_modified.append(after_snap)
            elif before_snap and before_snap.exists and not after_snap.exists:
                diff.files_deleted.append(before_snap)

        # 5. Browser Diffs
        diff.browser_url_before = before.browser.url
        diff.browser_url_after = after.browser.url
        if before.browser.url != after.browser.url and after.browser.url:
            diff.browser_navigated = True

        # 6. Screen text change
        if before.screen_signature and after.screen_signature:
            diff.screen_changed = (before.screen_signature != after.screen_signature)
        elif before.screen_text != after.screen_text:
            diff.screen_changed = True

        return diff
