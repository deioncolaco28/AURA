"""
app/automation/application_manager.py

Comprehensive Windows application lifecycle and window manager.
Supports registry lookup, alias normalization, process detection,
foreground verification, and window controls.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any

from app.automation.applications import (
    find_process_windows,
    find_standard_windows_path,
    find_windows_app_path_in_registry,
)
from app.perception.foreground_detector import (
    ApplicationContext,
    ForegroundApplicationDetector,
)

logger = logging.getLogger(__name__)


@dataclass
class AppRegistryEntry:
    """Registered application definition."""

    logical_name: str
    executable: str
    process_names: list[str]
    aliases: list[str] = field(default_factory=list)
    launch_args: list[str] = field(default_factory=list)
    description: str = ""


class ApplicationManager:
    """
    Manages Windows applications: discovery, launching, focus, window state, and termination.
    """

    DEFAULT_REGISTRY: dict[str, AppRegistryEntry] = {
        "notepad": AppRegistryEntry(
            logical_name="Notepad",
            executable="notepad.exe",
            process_names=["notepad.exe", "Notepad.exe"],
            aliases=["note pad", "windows notepad", "text editor"],
            description="Windows Notepad text editor",
        ),
        "calculator": AppRegistryEntry(
            logical_name="Calculator",
            executable="calc.exe",
            process_names=["calc.exe", "CalculatorApp.exe", "Calculator.exe"],
            aliases=["calc", "windows calculator"],
            description="Windows Calculator",
        ),
        "paint": AppRegistryEntry(
            logical_name="Paint",
            executable="mspaint.exe",
            process_names=["mspaint.exe", "PaintApp.exe"],
            aliases=["ms paint", "microsoft paint", "drawing"],
            description="Microsoft Paint",
        ),
        "explorer": AppRegistryEntry(
            logical_name="File Explorer",
            executable="explorer.exe",
            process_names=["explorer.exe", "Explorer.EXE"],
            aliases=["file explorer", "files", "my computer", "file manager", "this pc"],
            description="Windows File Explorer",
        ),
        "chrome": AppRegistryEntry(
            logical_name="Google Chrome",
            executable="chrome.exe",
            process_names=["chrome.exe"],
            aliases=["google chrome", "chrome browser", "google"],
            description="Google Chrome Web Browser",
        ),
        "edge": AppRegistryEntry(
            logical_name="Microsoft Edge",
            executable="msedge.exe",
            process_names=["msedge.exe"],
            aliases=["msedge", "microsoft edge", "edge browser"],
            description="Microsoft Edge Web Browser",
        ),
        "firefox": AppRegistryEntry(
            logical_name="Mozilla Firefox",
            executable="firefox.exe",
            process_names=["firefox.exe"],
            aliases=["mozilla", "mozilla firefox"],
            description="Mozilla Firefox Web Browser",
        ),
        "terminal": AppRegistryEntry(
            logical_name="Terminal",
            executable="wt.exe",
            process_names=["WindowsTerminal.exe", "wt.exe", "cmd.exe", "powershell.exe"],
            aliases=["windows terminal", "the terminal", "terminal", "console"],
            description="Windows Terminal / Console",
        ),
        "cmd": AppRegistryEntry(
            logical_name="Command Prompt",
            executable="cmd.exe",
            process_names=["cmd.exe"],
            aliases=["command prompt", "command line", "dos"],
            description="Windows Command Prompt",
        ),
        "powershell": AppRegistryEntry(
            logical_name="PowerShell",
            executable="powershell.exe",
            process_names=["powershell.exe", "pwsh.exe"],
            aliases=["windows powershell", "ps", "pwsh"],
            description="Windows PowerShell",
        ),
        "taskmgr": AppRegistryEntry(
            logical_name="Task Manager",
            executable="taskmgr.exe",
            process_names=["taskmgr.exe", "Taskmgr.exe"],
            aliases=["task manager", "taskmgr", "tasks"],
            description="Windows Task Manager",
        ),
        "snippingtool": AppRegistryEntry(
            logical_name="Snipping Tool",
            executable="snippingtool.exe",
            process_names=["SnippingTool.exe", "ScreenClippingHost.exe", "snippingtool.exe"],
            aliases=["snipping tool", "snip", "screenshot tool"],
            description="Windows Snipping Tool",
        ),
        "vscode": AppRegistryEntry(
            logical_name="Visual Studio Code",
            executable="code",
            process_names=["Code.exe", "code.exe"],
            aliases=["vs code", "vscode", "visual studio code", "code editor"],
            description="Visual Studio Code",
        ),
        "word": AppRegistryEntry(
            logical_name="Microsoft Word",
            executable="winword.exe",
            process_names=["WINWORD.EXE", "winword.exe"],
            aliases=["ms word", "microsoft word", "word document"],
            description="Microsoft Word",
        ),
        "excel": AppRegistryEntry(
            logical_name="Microsoft Excel",
            executable="excel.exe",
            process_names=["EXCEL.EXE", "excel.exe"],
            aliases=["ms excel", "microsoft excel", "spreadsheet"],
            description="Microsoft Excel",
        ),
        "powerpoint": AppRegistryEntry(
            logical_name="Microsoft PowerPoint",
            executable="powerpnt.exe",
            process_names=["POWERPNT.EXE", "powerpnt.exe"],
            aliases=["ms powerpoint", "powerpoint", "ppt"],
            description="Microsoft PowerPoint",
        ),
    }

    def __init__(
        self,
        foreground_detector: ForegroundApplicationDetector | None = None,
        registry: dict[str, AppRegistryEntry] | None = None,
    ):
        self.foreground_detector = foreground_detector or ForegroundApplicationDetector()
        self.registry = dict(registry or self.DEFAULT_REGISTRY)

        # Build alias lookup table
        self._alias_map: dict[str, str] = {}
        for key, entry in self.registry.items():
            self._alias_map[key.lower()] = key
            self._alias_map[entry.logical_name.lower()] = key
            for alias in entry.aliases:
                self._alias_map[alias.lower()] = key

    def resolve_application(self, query: str) -> AppRegistryEntry | None:
        """Resolve a query string or alias into a registered AppRegistryEntry."""
        if not query or not query.strip():
            return None
        q = query.strip().lower()
        key = self._alias_map.get(q)
        if key and key in self.registry:
            return self.registry[key]

        # Partial matching across logical names and aliases
        for reg_key, entry in self.registry.items():
            if q in entry.logical_name.lower() or any(q in a for a in entry.aliases):
                return entry

        return None

    def _resolve_executable_path(self, exe: str) -> str:
        """Resolve executable to absolute path using PATH, Registry, and standard directories."""
        if os.path.exists(exe):
            return exe
        if shutil.which(exe):
            return exe
        reg = find_windows_app_path_in_registry(exe)
        if reg:
            return reg
        std = find_standard_windows_path(exe)
        if std:
            return std
        return exe

    def launch(self, application: str, parameters: list[str] | None = None) -> subprocess.Popen:
        """Launch an application safely."""
        entry = self.resolve_application(application)
        args = parameters or []
        app_lower = application.strip().lower()

        if entry:
            executable = self._resolve_executable_path(entry.executable)
            launch_cmd = [executable] + entry.launch_args + args
        else:
            clean_app = application.strip()
            if clean_app.endswith(".exe") or os.path.exists(clean_app) or shutil.which(clean_app):
                executable = self._resolve_executable_path(clean_app)
                launch_cmd = [executable] + args
            else:
                raise ValueError(f"Unknown or unsupported application: '{application}'.")

        # Special handling for File Explorer to ensure a real GUI folder window opens
        if "explorer" in app_lower or executable.lower().endswith("explorer.exe"):
            if not args:
                target_dir = os.environ.get("USERPROFILE", "C:\\")
                launch_cmd = [executable, target_dir]

        creation_flags = 0
        if app_lower in ("powershell", "windows powershell", "cmd", "command prompt", "console"):
            creation_flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0x00000010)
        elif "terminal" in app_lower and executable.lower().endswith(("powershell.exe", "cmd.exe")):
            creation_flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0x00000010)

        try:
            if creation_flags:
                process = subprocess.Popen(launch_cmd, creationflags=creation_flags, shell=False)
            else:
                process = subprocess.Popen(launch_cmd, shell=False)
            return process
        except Exception as exc:
            logger.error(f"Failed to launch application '{application}': {exc}")
            raise RuntimeError(f"Could not launch application '{application}': {exc}") from exc

    def is_window_open(self, application: str) -> bool:
        """
        Check if an interactive GUI window is open for the given application.
        Distinguishes desktop shell and background services from real application windows.
        """
        entry = self.resolve_application(application)
        target_name = (entry.logical_name if entry else application).lower()
        target_procs = entry.process_names if entry else [f"{application}.exe" if not application.endswith(".exe") else application]

        # Special case for File Explorer:
        if "explorer" in target_name or any("explorer" in p.lower() for p in target_procs):
            wins = find_process_windows("explorer.exe")
            for w in wins:
                title = str(w.get("window_title", "")).lower()
                has_gui = w.get("has_gui_window", bool(title and title not in ("program manager", "desktop", "shell_traywnd", "n/a", "olemainthreadwndname", "")))
                if has_gui and title not in ("program manager", "desktop", "shell_traywnd", "n/a", "olemainthreadwndname", ""):
                    return True
            return False

        # Special case for Terminal:
        if "terminal" in target_name or any(p.lower() in ("terminal", "wt.exe", "windowsterminal.exe") for p in target_procs):
            wt_wins = find_process_windows("WindowsTerminal.exe") + find_process_windows("wt.exe")
            if wt_wins:
                return True
            ps_wins = find_process_windows("powershell.exe") + find_process_windows("cmd.exe")
            curr_pid = os.getpid()
            for w in ps_wins:
                pid = w.get("pid", 0)
                title = str(w.get("window_title", "")).lower()
                has_gui = w.get("has_gui_window", bool(title and title not in ("n/a", "olemainthreadwndname", "")))
                if pid != curr_pid and has_gui and title not in ("n/a", "olemainthreadwndname", ""):
                    return True
            return False

        # For general applications:
        for proc in target_procs:
            wins = find_process_windows(proc)
            if wins:
                return True

        return False

    def is_running(self, application: str) -> bool:
        """Check if an application is running / open."""
        # For system shell (explorer) and terminal host, require actual GUI window to avoid false positives
        app_lower = application.lower()
        if "explorer" in app_lower or "terminal" in app_lower or app_lower in ("powershell", "cmd"):
            return self.is_window_open(application)

        # For other applications:
        entry = self.resolve_application(application)
        target_processes = entry.process_names if entry else [application]
        target_lower = [p.lower() for p in target_processes]

        for proc in target_lower:
            wins = find_process_windows(proc)
            if wins:
                return True

        # Fallback to Windows tasklist command
        try:
            output = subprocess.check_output("tasklist", shell=True, text=True)
            for t in target_lower:
                if t in output.lower():
                    return True
        except Exception:
            pass

        return False

    def is_foreground(self, application: str) -> bool:
        """Check if the given application is currently the active foreground window."""
        ctx = self.foreground_detector.get_foreground_context()
        entry = self.resolve_application(application)
        if entry:
            if ctx.matches(entry.logical_name) or any(ctx.matches(a) for a in entry.aliases):
                return True
            for proc in entry.process_names:
                if ctx.matches(proc):
                    return True
        return ctx.matches(application)

    def focus(self, application: str) -> bool:
        """Bring the application window to the foreground."""
        entry = self.resolve_application(application)
        title_target = entry.logical_name if entry else application

        from app.automation.desktop_manager import DesktopManager
        dm = DesktopManager()
        return dm.focus_window(title_target)

    def minimize(self, application: str) -> bool:
        """Minimize the application window."""
        self.focus(application)
        from app.automation.desktop_manager import DesktopManager
        return DesktopManager().minimize_window()

    def maximize(self, application: str) -> bool:
        """Maximize the application window."""
        self.focus(application)
        from app.automation.desktop_manager import DesktopManager
        return DesktopManager().maximize_window()

    def restore(self, application: str) -> bool:
        """Restore the application window size."""
        self.focus(application)
        from app.automation.desktop_manager import DesktopManager
        return DesktopManager().restore_window()

    def close(self, application: str) -> bool:
        """Close the application window or process."""
        entry = self.resolve_application(application)
        target_procs = entry.process_names if entry else [application]

        # Try graceful window close first
        self.focus(application)
        from app.automation.desktop_manager import DesktopManager
        DesktopManager().close_window()

        # If still running, terminate matching processes safely
        try:
            import psutil  # type: ignore
            for proc in psutil.process_iter(["name"]):
                try:
                    name = (proc.info.get("name") or "").lower()
                    if any(t.lower() in name for t in target_procs):
                        proc.terminate()
                except Exception:
                    pass
        except Exception:
            pass

        return True
