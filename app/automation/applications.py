import subprocess


class ApplicationController:
    """Controls launching desktop applications."""

    def launch(self, application: str) -> None:
        """Launch an application by its Windows command/name."""

        if not application.strip():
            raise ValueError("Application name cannot be empty.")

        subprocess.Popen(
            application,
            shell=True,
        )