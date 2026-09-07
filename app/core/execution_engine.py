from typing import Callable

from app.core.execution import (
    ExecutionContext,
    ExecutionStep,
)
from app.core.replanner import (
    NoOpReplanner,
    Replanner,
)
from app.intelligence.action import Action
from app.intelligence.task import Task


class ExecutionEngine:
    """
    Executes tasks using an observe/act/verify/recover loop.

    Recovery has two levels:

    1. Retry the failed action.
    2. Ask the configured Replanner for replacement actions.

    The replanner is deliberately injected so the execution
    engine remains independent from any specific AI model.
    """

    def __init__(
        self,
        execute_action: Callable[[Action], Action],
        verify_action: Callable[[Action], None],
        max_retries: int = 1,
        replanner: Replanner | None = None,
        max_replans: int = 1,
    ):
        if max_retries < 0:
            raise ValueError(
                "max_retries cannot be negative."
            )

        if max_replans < 0:
            raise ValueError(
                "max_replans cannot be negative."
            )

        self.execute_action = execute_action
        self.verify_action = verify_action

        self.max_retries = max_retries

        self.replanner = (
            replanner
            or NoOpReplanner()
        )

        self.max_replans = max_replans

    def run(
        self,
        task: Task,
    ) -> ExecutionContext:
        """
        Execute a task while allowing bounded replanning.

        The action queue begins with task.actions.

        When an action fails after retries, the replanner may
        provide replacement actions.
        """

        context = ExecutionContext(
            goal=task.goal,
            total_steps=task.total_actions,
        )

        action_queue = list(
            task.actions
        )

        replan_count = 0

        while action_queue:

            action = action_queue.pop(0)

            context.current_step += 1

            step = context.add_step(
                action
            )

            self._run_step(
                step,
                context,
            )

            if step.status == "COMPLETED":
                continue

            if (
                replan_count
                >= self.max_replans
            ):
                break

            replan_count += 1

            replacement_actions = (
                self._replan(
                    task,
                    context,
                    action,
                )
            )

            if not replacement_actions:
                break

            print(
                f"Replanner produced "
                f"{len(replacement_actions)} "
                f"replacement action(s)."
            )

            action_queue = (
                replacement_actions
                + action_queue
            )

            context.metadata[
                "replan_count"
            ] = replan_count

        context.metadata[
            "replan_count"
        ] = replan_count

        return context

    def _run_step(
        self,
        step: ExecutionStep,
        context: ExecutionContext,
    ) -> None:
        """Execute one action with bounded retries."""

        total_attempts = (
            self.max_retries + 1
        )

        for attempt in range(
            1,
            total_attempts + 1,
        ):
            step.attempts = attempt
            step.status = "RUNNING"
            step.error = None

            try:
                print(
                    f"Action attempt "
                    f"{attempt}/{total_attempts}: "
                    f"{step.action.action_type}"
                )

                executed_action = (
                    self.execute_action(
                        step.action
                    )
                )

                self.verify_action(
                    executed_action
                )

                self._copy_execution_result(
                    step,
                    executed_action,
                )

                context.mark_completed(
                    step,
                    verification={
                        "success": True,
                        "attempt": attempt,
                    },
                )

                return

            except Exception as error:
                step.error = str(error)

                print(
                    f"Action attempt failed: "
                    f"{error}"
                )

                if attempt < total_attempts:
                    context.mark_recovering(
                        step
                    )

        context.mark_failed(
            step,
            step.error
            or "Unknown execution error.",
        )

    def _replan(
        self,
        task: Task,
        context: ExecutionContext,
        failed_action: Action,
    ) -> list[Action]:
        """Ask the configured replanner for new actions."""

        print(
            "Requesting replanning..."
        )

        try:
            actions = self.replanner.replan(
                task=task,
                context=context,
                failed_action=failed_action,
            )

        except Exception as error:
            print(
                f"Replanning failed: {error}"
            )
            return []

        if actions is None:
            return []

        if not isinstance(actions, list):
            raise TypeError(
                "Replanner must return a list of actions."
            )

        for action in actions:
            if not isinstance(
                action,
                Action,
            ):
                raise TypeError(
                    "Replanner returned a non-Action value."
                )

        return actions

    def _copy_execution_result(
        self,
        step: ExecutionStep,
        action: Action,
    ) -> None:
        """Preserve the action execution result."""

        if action.execution_result:
            step.verification.update(
                action.execution_result
            )