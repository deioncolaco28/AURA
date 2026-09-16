import subprocess

from app.verification.verifier import (
    VerificationResult,
    Verifier,
)


class ApplicationVerifier(Verifier):
    """
    Verifies whether a Windows process/application is running.

    Supports both:

        verifier.verify("notepad.exe")

    and:

        verifier.verify(action)

    where action.verification contains:

        {
            "type": "APPLICATION_RUNNING",
            "process": "notepad.exe"
        }
    """

    def verify(
        self,
        action,
    ) -> VerificationResult:

        process = self._extract_process(
            action
        )

        if not process:
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

        except Exception as error:
            return VerificationResult(
                success=False,
                message=str(error),
                verification_type=(
                    "APPLICATION_RUNNING"
                ),
                metadata={
                    "process": process,
                },
            )

        running = (
            process.lower()
            in result.stdout.lower()
        )

        if running:
            return VerificationResult(
                success=True,
                message=(
                    f"{process} is running."
                ),
                verification_type=(
                    "APPLICATION_RUNNING"
                ),
                metadata={
                    "process": process,
                },
            )

        return VerificationResult(
            success=False,
            message=(
                f"{process} is not running."
            ),
            verification_type=(
                "APPLICATION_RUNNING"
            ),
            metadata={
                "process": process,
            },
        )

    @staticmethod
    def _extract_process(
        action,
    ) -> str:
        """
        Extract the process name from either a string
        or an AURA Action.
        """

        if isinstance(
            action,
            str,
        ):
            return action.strip()

        verification = getattr(
            action,
            "verification",
            {},
        )

        process = verification.get(
            "process"
        )

        if process:
            return str(
                process
            ).strip()

        target = getattr(
            action,
            "target",
            None,
        )

        if target:
            return str(
                target
            ).strip()

        return ""