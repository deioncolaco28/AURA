import subprocess

from app.verification.verifier import (
    VerificationResult,
    Verifier,
)


class ApplicationVerifier(Verifier):
    """Verifies whether a Windows application is running."""

    def verify(
        self,
        application_name: str,
    ) -> VerificationResult:
        """Check whether an application is running."""

        if not application_name.strip():
            return VerificationResult(
                success=False,
                message="Application name cannot be empty.",
            )

        result = subprocess.run(
            [
                "tasklist",
                "/FI",
                f"IMAGENAME eq {application_name}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        output = result.stdout.lower()

        application_found = (
            application_name.lower() in output
        )

        if application_found:
            return VerificationResult(
                success=True,
                message=(
                    f"{application_name} is running."
                ),
            )

        return VerificationResult(
            success=False,
            message=(
                f"{application_name} is not running."
            ),
        )