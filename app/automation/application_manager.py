"""
app/automation/application_manager.py

Comprehensive Windows application lifecycle and window manager.
Supports registry lookup, alias normalization, process detection,
foreground verification, and window controls.
"""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass, field
from typing import Any

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
        "cmd": AppRegistryEntry(
            logical_name="Command Prompt",
            executable="cmd.exe",
            process_names=["cmd.exe"],
            aliases=["command prompt", "terminal", "command line", "dos"],
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

    def launch(self, application: str, parameters: list[str] | None = None) -> subprocess.Popen:
        """Launch an application safely."""
        entry = self.resolve_application(application)
        args = parameters or []

        if entry:
            executable = entry.executable
            launch_cmd = [executable] + entry.launch_args + args
        else:
            # Generic fallback for direct executable path
            clean_app = application.strip()
            if clean_app.endswith(".exe") or os.path.exists(clean_app):
                launch_cmd = [clean_app] + args
            else:
                raise ValueError(f"Unknown or unsupported application: '{application}'.")

        try:
            process = subprocess.Popen(launch_cmd, shell=False)
            return process
        except Exception as exc:
            logger.error(f"Failed to launch application '{application}': {exc}")
            raise RuntimeError(f"Could not launch application '{application}': {exc}") from exc

    def is_running(self, application: str) -> bool:
        """Check if any process matching the application is currently running."""
        entry = self.resolve_application(application)
        target_processes = entry.process_names if entry else [application]
        target_lower = [p.lower() for p in target_processes]

        try:
            import psutil  # type: ignore
            for proc in psutil.process_iter(["name"]):
                try:
                    name = (proc.info.get("name") or "").lower()
                    if any(t in name for t in target_lower):
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except ImportError:
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
