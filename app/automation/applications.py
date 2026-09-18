import subprocess


class ApplicationController:
    """
    Safely launches a predefined set of supported Windows applications.

    AURA should not execute arbitrary user-provided shell commands.
    Applications are resolved through a controlled registry.
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
    }

    def resolve(self, application: str) -> str:
        if not application or not application.strip():
            raise ValueError("Application name cannot be empty.")

        normalized = application.strip().lower()

        executable = self.APPLICATION_REGISTRY.get(normalized)

        if executable is None:
            raise ValueError(
                f"Unsupported application: {application}"
            )

        return executable

    def launch(self, application: str) -> None:
        executable = self.resolve(application)

        subprocess.Popen(
            [executable],
            shell=False,
        )