import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config.settings import settings


class AURALogger:
    """Lightweight structured logger for AURA."""

    def __init__(
        self,
        log_directory: str | None = None,
    ):
        self.log_directory = Path(
            log_directory
            or settings.log_directory
        )

        self.log_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.log_file = (
            self.log_directory
            / "aura.log"
        )

    def log(
        self,
        event: str,
        message: str = "",
        **metadata: Any,
    ) -> None:
        """Write one structured event."""

        record = {
            "timestamp": (
                datetime.now().isoformat()
            ),
            "event": event,
            "message": message,
            "metadata": metadata,
        }

        with self.log_file.open(
            "a",
            encoding="utf-8",
        ) as file:
            file.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )

    def command_received(
        self,
        command: str,
    ) -> None:
        self.log(
            "COMMAND_RECEIVED",
            "User command received.",
            command=command,
        )

    def intent_detected(
        self,
        goal: str,
        mode: str,
        risk: str,
    ) -> None:
        self.log(
            "INTENT_DETECTED",
            "Intent successfully parsed.",
            goal=goal,
            mode=mode,
            risk=risk,
        )

    def action_executed(
        self,
        action_type: str,
        success: bool,
    ) -> None:
        self.log(
            "ACTION_EXECUTED",
            "Action execution completed.",
            action_type=action_type,
            success=success,
        )

    def verification(
        self,
        verification_type: str,
        success: bool,
    ) -> None:
        self.log(
            "VERIFICATION",
            "Verification completed.",
            verification_type=verification_type,
            success=success,
        )

    def task_completed(
        self,
        goal: str,
    ) -> None:
        self.log(
            "TASK_COMPLETED",
            "Task completed successfully.",
            goal=goal,
        )

    def task_failed(
        self,
        goal: str,
        error: str = "",
    ) -> None:
        self.log(
            "TASK_FAILED",
            "Task failed.",
            goal=goal,
            error=error,
        )