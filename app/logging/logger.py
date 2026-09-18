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

    def tutoring_step_started(
        self,
        step_index: int,
        total_steps: int,
        action_type: str | None = None,
    ) -> None:
        self.log(
            "TUTORING_STEP_STARTED",
            f"Tutoring step {step_index}/{total_steps} started.",
            step_index=step_index,
            total_steps=total_steps,
            action_type=action_type,
        )

    def tutoring_instruction_given(
        self,
        instruction: str,
    ) -> None:
        self.log(
            "TUTORING_INSTRUCTION_GIVEN",
            "Tutoring instruction spoken.",
            instruction=instruction,
        )

    def tutoring_waiting_for_user(
        self,
        step_index: int,
    ) -> None:
        self.log(
            "TUTORING_WAITING_FOR_USER",
            f"Waiting for user on step {step_index}.",
            step_index=step_index,
        )

    def tutoring_observation(
        self,
        elements_count: int,
        processes_count: int = 0,
    ) -> None:
        self.log(
            "TUTORING_OBSERVATION",
            "Screen observed for tutoring verification.",
            elements_count=elements_count,
            processes_count=processes_count,
        )

    def tutoring_target_resolved(
        self,
        target: str,
        description: str = "",
    ) -> None:
        self.log(
            "TUTORING_TARGET_RESOLVED",
            "Tutoring target resolved.",
            target=target,
            description=description,
        )

    def tutoring_verification_passed(
        self,
        step_index: int,
        strategy: str = "",
    ) -> None:
        self.log(
            "TUTORING_VERIFICATION_PASSED",
            f"Tutoring step {step_index} verification passed.",
            step_index=step_index,
            strategy=strategy,
        )

    def tutoring_verification_failed(
        self,
        step_index: int,
        reason: str = "",
    ) -> None:
        self.log(
            "TUTORING_VERIFICATION_FAILED",
            f"Tutoring step {step_index} verification check failed.",
            step_index=step_index,
            reason=reason,
        )

    def tutoring_recovery(
        self,
        step_index: int,
        attempt: int,
    ) -> None:
        self.log(
            "TUTORING_RECOVERY",
            f"Tutoring recovery initiated for step {step_index} (attempt {attempt}).",
            step_index=step_index,
            attempt=attempt,
        )

    def tutoring_step_completed(
        self,
        step_index: int,
    ) -> None:
        self.log(
            "TUTORING_STEP_COMPLETED",
            f"Tutoring step {step_index} completed.",
            step_index=step_index,
        )

    def tutoring_task_completed(
        self,
        success: bool,
    ) -> None:
        self.log(
            "TUTORING_TASK_COMPLETED",
            "Tutoring task finished.",
            success=success,
        )