import os
import subprocess

from app.automation.applications import find_process_windows
from app.verification.verifier import (
    VerificationResult,
    Verifier,
)


class ApplicationVerifier(Verifier):
    """
    Verifies whether a Windows application/process is running.

    Supports:

        verifier.verify("notepad.exe")

    and:

        verifier.verify(action)

    where action.verification may contain:

        {
            "type": "APPLICATION_RUNNING",
            "process": "notepad.exe"
        }

    or:

        {
            "type": "APPLICATION_RUNNING",
            "processes": [
                "CalculatorApp.exe",
                "Calculator.exe"
            ]
        }
    """

    def verify(
        self,
        action,
    ) -> VerificationResult:

        processes = self._extract_processes(
            action
        )

        if not processes:
            return VerificationResult(
                success=False,
                message=(
                    "Application/process name "
                    "cannot be empty."
                ),
                verification_type=(
                    "APPLICATION_RUNNING"
                ),
            )

        running_process = self._find_running_process(
            processes
        )

        if running_process is not None:
            return VerificationResult(
                success=True,
                message=(
                    f"{running_process} is running."
                ),
                verification_type=(
                    "APPLICATION_RUNNING"
                ),
                metadata={
                    "process": running_process,
                    "checked_processes": processes,
                },
            )

        process_text = ", ".join(processes)

        return VerificationResult(
            success=False,
            message=(
                f"{processes[0]} is not running."
                if len(processes) == 1
                else (
                    f"None of the expected processes "
                    f"are running: {process_text}."
                )
            ),
            verification_type=(
                "APPLICATION_RUNNING"
            ),
            metadata={
                "processes": processes,
            },
        )

    def _find_running_process(
        self,
        processes: list[str],
    ) -> str | None:
        # Check if we are verifying File Explorer or Terminal specially
        is_explorer_check = any("explorer" in p.lower() for p in processes)
        is_terminal_check = any(p.lower() in ("terminal", "wt.exe", "windowsterminal.exe", "powershell.exe", "cmd.exe") for p in processes)

        for process in processes:
            p_lower = process.lower()

            # For File Explorer: must verify an actual GUI window is open, NOT just background shell
            if "explorer" in p_lower:
                wins = find_process_windows("explorer.exe")
                for w in wins:
                    title = str(w.get("window_title", "")).lower()
                    has_gui = w.get("has_gui_window", bool(title and title not in ("program manager", "desktop", "shell_traywnd", "n/a", "olemainthreadwndname", "")))
                    if has_gui and title not in ("program manager", "desktop", "shell_traywnd", "n/a", "olemainthreadwndname", ""):
                        return "explorer.exe"
                continue

            # For Terminal / PowerShell / CMD:
            if p_lower in ("terminal", "wt.exe", "windowsterminal.exe"):
                wt_wins = find_process_windows("WindowsTerminal.exe") + find_process_windows("wt.exe")
                if wt_wins:
                    return "wt.exe"
                continue

            if p_lower in ("powershell.exe", "cmd.exe", "powershell", "cmd"):
                clean_p = process if process.endswith(".exe") else f"{process}.exe"
                wins = find_process_windows(clean_p)
                curr_pid = os.getpid()
                for w in wins:
                    pid = w.get("pid", 0)
                    title = str(w.get("window_title", "")).lower()
                    has_gui = w.get("has_gui_window", bool(title and title not in ("n/a", "olemainthreadwndname", "")))
                    if pid != curr_pid and has_gui and title not in ("n/a", "olemainthreadwndname", ""):
                        return process
                continue

            # For general applications (notepad, calc, chrome, etc.):
            clean_p = process if process.endswith(".exe") else f"{process}.exe"
            wins = find_process_windows(clean_p)
            if wins:
                return process

            # Fallback to tasklist /FI
            try:
                result = subprocess.run(
                    [
                        "tasklist",
                        "/FI",
                        f"IMAGENAME eq {process}",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if process.lower() in result.stdout.lower():
                    return process
            except Exception:
                continue

        return None

    @staticmethod
    def _extract_processes(
        action,
    ) -> list[str]:
        """
        Extract process names from either a string
        or an AURA Action.
        """

        if isinstance(action, str):
            process = action.strip()

            return [process] if process else []

        verification = getattr(
            action,
            "verification",
            {},
        )

        processes = verification.get(
            "processes"
        )

        if processes:
            if isinstance(
                processes,
                str,
            ):
                processes = [processes]

            return [
                str(process).strip()
                for process in processes
                if str(process).strip()
            ]

        process = verification.get(
            "process"
        )

        if process:
            return [str(process).strip()]

        target = getattr(
            action,
            "target",
            None,
        )

        if target:
            return [str(target).strip()]

        return []

    @staticmethod
    def _extract_process(
        action,
    ) -> str:
        """
        Backward-compatible helper used by existing tests/code.
        """

        processes = (
            ApplicationVerifier
            ._extract_processes(action)
        )

        if processes:
            return processes[0]

        return ""