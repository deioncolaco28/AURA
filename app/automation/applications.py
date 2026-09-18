import os
import shutil
import subprocess
import sys
from typing import Any


def find_windows_app_path_in_registry(exe_name: str) -> str | None:
    """Check Windows App Paths registry for registered executable paths."""
    if sys.platform != "win32":
        return None
    try:
        import winreg

        for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for subkey in (
                rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}",
                rf"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}",
            ):
                try:
                    with winreg.OpenKey(root, subkey) as key:
                        val, _ = winreg.QueryValueEx(key, "")
                        if val and os.path.exists(val):
                            return val
                except OSError:
                    continue
    except Exception:
        pass
    return None


def find_standard_windows_path(exe_name: str) -> str | None:
    """Check standard installation directories for common Windows applications."""
    exe_lower = exe_name.lower()

    candidates: list[str] = []

    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    system32 = os.path.join(system_root, "System32")

    if "chrome" in exe_lower:
        candidates.extend(
            [
                os.path.join(program_files, "Google", "Chrome", "Application", "chrome.exe"),
                os.path.join(program_files_x86, "Google", "Chrome", "Application", "chrome.exe"),
                os.path.join(local_app_data, "Google", "Chrome", "Application", "chrome.exe"),
            ]
        )
    elif "msedge" in exe_lower or "edge" in exe_lower:
        candidates.extend(
            [
                os.path.join(program_files, "Microsoft", "Edge", "Application", "msedge.exe"),
                os.path.join(program_files_x86, "Microsoft", "Edge", "Application", "msedge.exe"),
            ]
        )
    elif "firefox" in exe_lower:
        candidates.extend(
            [
                os.path.join(program_files, "Mozilla Firefox", "firefox.exe"),
                os.path.join(program_files_x86, "Mozilla Firefox", "firefox.exe"),
            ]
        )
    elif "wt" in exe_lower or "terminal" in exe_lower:
        candidates.extend(
            [
                os.path.join(local_app_data, "Microsoft", "WindowsApps", "wt.exe"),
                os.path.join(system32, "WindowsPowerShell", "v1.0", "powershell.exe"),
                os.path.join(system32, "cmd.exe"),
            ]
        )
    elif "powershell" in exe_lower or "pwsh" in exe_lower:
        candidates.extend(
            [
                os.path.join(system32, "WindowsPowerShell", "v1.0", "powershell.exe"),
                os.path.join(program_files, "PowerShell", "7", "pwsh.exe"),
            ]
        )
    elif "cmd" in exe_lower:
        candidates.extend([os.path.join(system32, "cmd.exe")])
    elif "notepad" in exe_lower:
        candidates.extend(
            [
                os.path.join(system32, "notepad.exe"),
                os.path.join(system_root, "notepad.exe"),
                os.path.join(local_app_data, "Microsoft", "WindowsApps", "notepad.exe"),
            ]
        )
    elif "calc" in exe_lower:
        candidates.extend(
            [
                os.path.join(system32, "calc.exe"),
                os.path.join(system_root, "calc.exe"),
            ]
        )
    elif "mspaint" in exe_lower or "paint" in exe_lower:
        candidates.extend(
            [
                os.path.join(system32, "mspaint.exe"),
                os.path.join(system_root, "mspaint.exe"),
            ]
        )
    elif "explorer" in exe_lower:
        candidates.extend(
            [
                os.path.join(system_root, "explorer.exe"),
                os.path.join(system32, "explorer.exe"),
            ]
        )

    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate

    return None


def find_process_windows(exe_name: str) -> list[dict[str, Any]]:
    """Query tasklist for the given executable name and return list of window info dicts."""
    import csv
    import io
    windows = []
    clean_exe = exe_name if exe_name.lower().endswith(".exe") else f"{exe_name}.exe"
    try:
        cmd = ["tasklist", "/FI", f"IMAGENAME eq {clean_exe}", "/V", "/FO", "CSV"]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=3)
        if res.stdout:
            reader = csv.reader(io.StringIO(res.stdout))
            rows = list(reader)
            for row in rows:
                if len(row) >= 9 and row[0].lower().endswith(".exe"):
                    pname = row[0]
                    pid = int(row[1]) if row[1].isdigit() else 0
                    title = row[8]
                    has_gui = bool(
                        title
                        and title not in ("N/A", "OleMainThreadWndName", "DDE Server Window", ".NET-BroadcastEventWindow.3b95145.0")
                        and not title.startswith("MSCTFIME")
                    )
                    windows.append({
                        "process_name": pname,
                        "pid": pid,
                        "window_title": title,
                        "has_gui_window": has_gui,
                    })
    except Exception:
        pass
    return windows


class ApplicationController:
    """
    Safely launches a predefined set of supported Windows applications.

    AURA should not execute arbitrary user-provided shell commands.
    Applications are resolved through a multi-tier resolution mechanism:
    1. PATH lookup via shutil.which
    2. Windows App Paths registry
    3. Standard Windows installation directories
    """

    APPLICATION_REGISTRY = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "paint": "mspaint.exe",
        "explorer": "explorer.exe",
        "file explorer": "explorer.exe",
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "edge": "msedge.exe",
        "msedge": "msedge.exe",
        "microsoft edge": "msedge.exe",
        "firefox": "firefox.exe",
        "mozilla firefox": "firefox.exe",
        "terminal": "wt.exe",
        "the terminal": "wt.exe",
        "windows terminal": "wt.exe",
        "cmd": "cmd.exe",
        "command prompt": "cmd.exe",
        "powershell": "powershell.exe",
        "windows powershell": "powershell.exe",
        "console": "cmd.exe",
    }

    def _resolve_executable_path(self, exe: str) -> str:
        """Resolve executable to absolute path using PATH, Registry, and standard directories."""
        if os.path.exists(exe):
            return exe
        which = shutil.which(exe)
        if which:
            return which
        reg = find_windows_app_path_in_registry(exe)
        if reg:
            return reg
        std = find_standard_windows_path(exe)
        if std:
            return std
        return exe

    def resolve(self, application: str) -> str:
        """Resolve an application name or alias to an executable path."""
        if not application or not application.strip():
            raise ValueError("Application name cannot be empty.")

        normalized = application.strip().lower()

        # If it's already an existing executable file path
        if os.path.exists(application.strip()):
            return application.strip()

        executable = self.APPLICATION_REGISTRY.get(normalized)

        if executable is None:
            # Check if user passed an executable name directly like notepad.exe
            if normalized.endswith(".exe") or shutil.which(normalized):
                executable = normalized
            else:
                raise ValueError(f"Unsupported application: {application}")

        # Multi-tier path resolution:
        # Tier 1: Check PATH
        path_which = shutil.which(executable)
        if path_which:
            return path_which

        # Tier 2: Check Windows Registry App Paths
        reg_path = find_windows_app_path_in_registry(executable)
        if reg_path:
            return reg_path

        # Tier 3: Check Standard installation directories
        std_path = find_standard_windows_path(executable)
        if std_path:
            return std_path

        # Fallback to the executable name
        return executable

    def launch(self, application: str) -> None:
        """Launch an application executable safely."""
        executable = self.resolve(application)
        app_lower = application.strip().lower()

        # Special launch handling for Windows Shell (File Explorer)
        if "explorer" in app_lower or executable.lower().endswith("explorer.exe"):
            target_dir = os.environ.get("USERPROFILE", "C:\\")
            subprocess.Popen([executable, target_dir], shell=False)
            return

        # Special launch handling for Terminal / Console GUI
        if "terminal" in app_lower or "the terminal" in app_lower or "windows terminal" in app_lower:
            wt_path = self._resolve_executable_path("wt.exe")
            if wt_path and os.path.exists(wt_path):
                subprocess.Popen([wt_path], shell=False)
                return
            # Fallback to PowerShell in a new GUI console window
            ps_path = self._resolve_executable_path("powershell.exe")
            creation_flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0x00000010)
            subprocess.Popen([ps_path], creationflags=creation_flags, shell=False)
            return

        if app_lower in ("powershell", "windows powershell", "cmd", "command prompt", "console"):
            creation_flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0x00000010)
            subprocess.Popen([executable], creationflags=creation_flags, shell=False)
            return

        subprocess.Popen(
            [executable],
            shell=False,
        )