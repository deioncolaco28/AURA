import subprocess

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

        for process in processes:
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

            except Exception:
                continue

            if process.lower() in (
                result.stdout.lower()
            ):
                return process

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