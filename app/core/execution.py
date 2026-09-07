from dataclasses import dataclass, field
from typing import Any

from app.intelligence.action import Action


@dataclass
class ExecutionStep:
    """Records the execution history of one action."""

    index: int
    action: Action

    status: str = "PENDING"
    attempts: int = 0

    error: str | None = None

    verification: dict[str, Any] = field(
        default_factory=dict
    )

    recovery_attempted: bool = False


@dataclass
class ExecutionContext:
    """
    Stores runtime information for one task execution.

    Failed historical steps remain recorded, but a task can
    still be considered successful if a replanned replacement
    completes the intended work.
    """

    goal: str
    total_steps: int

    current_step: int = 0

    steps: list[ExecutionStep] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    @property
    def completed(self) -> bool:
        """
        Return True when the task's active execution path
        has successfully completed.

        Historical failed steps caused by replanning do not
        automatically make the overall task unsuccessful.
        """

        if not self.steps:
            return False

        if self.failed and not self.was_replanned_successfully:
            return False

        return self.steps[-1].status == "COMPLETED"

    @property
    def failed(self) -> bool:
        """Return True when an execution step failed."""

        return any(
            step.status == "FAILED"
            for step in self.steps
        )

    @property
    def was_replanned_successfully(self) -> bool:
        """
        Return True when replanning occurred and the latest
        execution path completed successfully.
        """

        return (
            self.metadata.get(
                "replan_count",
                0,
            )
            > 0
            and bool(self.steps)
            and self.steps[-1].status
            == "COMPLETED"
        )

    @property
    def current_execution_step(
        self,
    ) -> ExecutionStep | None:
        """Return the most recently registered step."""

        if not self.steps:
            return None

        return self.steps[-1]

    def add_step(
        self,
        action: Action,
    ) -> ExecutionStep:
        """Register a new action execution."""

        step = ExecutionStep(
            index=len(self.steps) + 1,
            action=action,
        )

        self.steps.append(step)

        return step

    def mark_completed(
        self,
        step: ExecutionStep,
        verification: dict[str, Any] | None = None,
    ) -> None:
        """Mark a step as successfully completed."""

        step.status = "COMPLETED"

        if verification is not None:
            step.verification = verification

    def mark_failed(
        self,
        step: ExecutionStep,
        error: str,
    ) -> None:
        """Mark a step as failed."""

        step.status = "FAILED"
        step.error = error

    def mark_recovering(
        self,
        step: ExecutionStep,
    ) -> None:
        """Mark a step as being recovered."""

        step.status = "RECOVERING"
        step.recovery_attempted = True