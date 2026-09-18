"""
app/core/execution_engine.py

Closed-loop execution engine for AURA tasks and task graphs.
Coordinates pre-action observation, precondition checks, execution, post-action observation,
state diff comparison, failure classification, and deterministic recovery.
"""

from __future__ import annotations

from typing import Any, Callable

from app.core.execution import (
    ExecutionContext,
    ExecutionStep,
)
from app.core.failure import (
    FailureClassifier,
    FailureInfo,
    FailureType,
)
from app.core.observation import ScreenObservation
from app.core.observation_diff import diff_observations
from app.core.observer import (
    ComputerObserver,
    ScreenObserver,
)
from app.core.recovery_engine import RecoveryEngine, RecoveryStrategyType
from app.core.replanner import (
    NoOpReplanner,
    Replanner,
)
from app.intelligence.action import (
    Action,
    ActionType,
)
from app.intelligence.expected_state import ExpectedState, StateComparator
from app.intelligence.task import Task
from app.intelligence.task_context import EntityResolver, TaskContext
from app.intelligence.task_graph import NodeStatus, TaskGraph, TaskNode


class ExecutionEngine:
    """
    Executes tasks using a closed-loop observe/act/verify/recover loop.
    Supports Task and TaskGraph models with context tracking and hierarchical recovery.
    """

    def __init__(
        self,
        execute_action: Callable[[Action], Action],
        verify_action: Callable[[Action], None],
        max_retries: int = 1,
        replanner: Replanner | None = None,
        max_replans: int = 1,
        observer: ComputerObserver | None = None,
        state_verifier: Any = None,
        task_context: TaskContext | None = None,
    ):
        if max_retries < 0:
            raise ValueError("max_retries cannot be negative.")

        if max_replans < 0:
            raise ValueError("max_replans cannot be negative.")

        self.execute_action = execute_action
        self.verify_action = verify_action
        self.max_retries = max_retries
        self.replanner = replanner or NoOpReplanner()
        self.max_replans = max_replans
        self.observer = observer or ScreenObserver()
        self.state_verifier = state_verifier
        self.task_context = task_context or TaskContext()

        self.failure_classifier = FailureClassifier()
        self.recovery_engine = RecoveryEngine(replanner=self.replanner)
        self.state_comparator = StateComparator()
        self.entity_resolver = EntityResolver(self.task_context)

    def run(
        self,
        task_or_graph: Task | TaskGraph,
    ) -> ExecutionContext:
        """
        Execute a Task or TaskGraph while allowing bounded replanning.
        """
        if isinstance(task_or_graph, TaskGraph):
            return self.run_graph(task_or_graph)

        task = task_or_graph
        context = ExecutionContext(
            goal=task.goal,
            total_steps=task.total_actions,
        )
        self.task_context.goal = task.goal

        action_queue = list(task.actions)
        replan_count = 0

        while action_queue:
            action = action_queue.pop(0)
            context.current_step += 1

            # Resolve contextual entity variables (e.g. $report, $folder)
            if action.target:
                action.target = self.entity_resolver.resolve(action.target)
            if isinstance(action.value, str):
                action.value = self.entity_resolver.resolve(action.value)

            step = context.add_step(action)
            self._run_step(step, context)

            if step.status == "COMPLETED":
                # Update context entities from successful action execution results
                if action.execution_result:
                    for k, v in action.execution_result.items():
                        self.task_context.set_entity(k, v)
                continue

            if replan_count >= self.max_replans:
                break

            replan_count += 1
            observation = self._observe()
            failure = self._build_failure_info(step)

            # Recovery engine check (if replanner is active)
            if not isinstance(self.replanner, NoOpReplanner):
                recovery_plan = self.recovery_engine.plan_recovery(failure, observation, self.task_context)
                if recovery_plan.actions:
                    action_queue = recovery_plan.actions + action_queue
                    context.metadata["replan_count"] = replan_count
                    continue

            # Replanner fallback
            replacement_actions = self._replan(
                task=task,
                context=context,
                failed_action=action,
                observation=observation,
                failure=failure,
            )

            if not replacement_actions:
                break

            print(f"Replanner produced {len(replacement_actions)} replacement action(s).")
            action_queue = replacement_actions + action_queue
            context.metadata["replan_count"] = replan_count

        context.metadata["replan_count"] = replan_count
        return context

    def run_graph(self, graph: TaskGraph) -> ExecutionContext:
        """
        Execute a TaskGraph respecting node dependencies, conditions, and states.
        """
        context = ExecutionContext(
            goal=graph.goal,
            total_steps=len(graph),
        )
        self.task_context.goal = graph.goal
        self.task_context.pending_tasks = [n.task_id for n in graph.nodes]

        while not graph.is_completed() and not graph.is_failed() and not graph.is_cancelled():
            ready_nodes = graph.get_ready_nodes()
            if not ready_nodes:
                # If no ready nodes and not completed, remaining nodes are blocked
                break

            for node in ready_nodes:
                if graph.is_cancelled():
                    break

                self.task_context.current_task_id = node.task_id
                graph.mark_running(node.task_id)

                # Check condition if present (branching / skipping)
                if node.condition:
                    obs_pre = self._observe()
                    cond_met = node.condition.evaluate(obs_pre, self.task_context, self.state_verifier)
                    if cond_met:
                        graph.mark_skipped(node.task_id, reason="Condition already met.")
                        self.task_context.record_completed(node.task_id)
                        continue

                # Precondition / Idempotency check for filesystem or app launch
                if node.action and self._is_already_satisfied(node.action):
                    graph.mark_skipped(node.task_id, reason="Action effect already satisfied.")
                    self.task_context.record_completed(node.task_id)
                    continue

                if node.action:
                    # Resolve context variables
                    if node.action.target:
                        node.action.target = self.entity_resolver.resolve(node.action.target)
                    if isinstance(node.action.value, str):
                        node.action.value = self.entity_resolver.resolve(node.action.value)

                    context.current_step += 1
                    step = context.add_step(node.action)

                    self._run_step(step, context, expected_state=node.expected_state)

                    if step.status == "COMPLETED":
                        graph.mark_completed(node.task_id, result=node.action.execution_result)
                        self.task_context.record_completed(node.task_id)
                        if node.action.execution_result:
                            for k, v in node.action.execution_result.items():
                                self.task_context.set_entity(k, v)
                    else:
                        failure_info = self._build_failure_info(step)
                        graph.mark_failed(node.task_id, failure_info=failure_info)
                        self.task_context.record_failure(failure_info)
                        break

        return context

    def _run_step(
        self,
        step: ExecutionStep,
        context: ExecutionContext,
        expected_state: ExpectedState | None = None,
    ) -> None:
        """Execute one action with bounded retries and state comparison."""
        total_attempts = self.max_retries + 1

        for attempt in range(1, total_attempts + 1):
            step.attempts = attempt
            step.status = "RUNNING"
            step.error = None

            obs_before = self._observe()

            try:
                print(f"Action attempt {attempt}/{total_attempts}: {step.action.action_type}")
                executed_action = self.execute_action(step.action) or step.action
            except Exception as error:
                step.error = str(error)
                failure_info = self.failure_classifier.classify(
                    action=step.action,
                    error=str(error),
                    attempt=attempt,
                )
                step.verification = {
                    "success": False,
                    "failure_type": failure_info.failure_type,
                }
                print(f"Action attempt failed: {error}")
                if attempt < total_attempts and failure_info.recoverability:
                    context.mark_recovering(step)
                continue

            obs_after = self._observe()
            diff = diff_observations(obs_before, obs_after, target=executed_action.target)

            # Verification pass: check custom verifier & state comparator
            try:
                self.verify_action(executed_action)
                self._copy_execution_result(step, executed_action)

                if expected_state:
                    comp_res = self.state_comparator.compare(
                        expected=expected_state,
                        observation=obs_after,
                        diff=diff,
                        system_verifier=self.state_verifier,
                    )
                    if not comp_res.success:
                        raise RuntimeError(comp_res.explanation)

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
                failure_info = self.failure_classifier.classify(
                    action=executed_action,
                    error=str(error),
                    diff=diff,
                    observation=obs_after,
                    attempt=attempt,
                )
                step.verification = {
                    "success": False,
                    "failure_type": failure_info.failure_type,
                    "type": executed_action.verification.get("type"),
                }
                print(f"Verification failed: {error}")
                if attempt < total_attempts and failure_info.recoverability:
                    context.mark_recovering(step)

        failure_type = step.verification.get("failure_type", FailureType.UNKNOWN)
        if failure_type == FailureType.VERIFICATION:
            failure_message = "Verification failed: " + (step.error or "Unknown verification error.")
        else:
            failure_message = step.error or f"Action failed ({failure_type})."

        context.mark_failed(step, failure_message)

    def _observe(self) -> ScreenObservation:
        """Capture current computer state."""
        try:
            return self.observer.observe()
        except Exception as error:
            return ScreenObservation(
                metadata={
                    "observation_failed": True,
                    "error": str(error),
                }
            )

    def _replan(
        self,
        task: Task,
        context: ExecutionContext,
        failed_action: Action,
        observation: ScreenObservation,
        failure: FailureInfo,
    ) -> list[Action]:
        """Ask the replanner for recovery actions."""
        try:
            actions = self.replanner.replan(
                task=task,
                context=context,
                failed_action=failed_action,
                observation=observation,
                failure=failure,
            )
            return actions if isinstance(actions, list) else []
        except Exception as error:
            print(f"Replanning failed: {error}")
            return []

    def _build_failure_info(self, step: ExecutionStep) -> FailureInfo:
        """Construct structured FailureInfo from execution step."""
        ftype = step.verification.get("failure_type", FailureType.UNKNOWN)
        return FailureInfo(
            action=step.action,
            error=step.error,
            verification=dict(step.action.verification | step.verification),
            attempt=step.attempts,
            failure_type=ftype,
            metadata={"step_index": step.index, "status": step.status},
        )

    def _copy_execution_result(self, step: ExecutionStep, action: Action) -> None:
        """Preserve action execution result dictionary."""
        result = getattr(action, "execution_result", None)
        if isinstance(result, dict) and result:
            step.verification.update(result)

    def _is_already_satisfied(self, action: Action) -> bool:
        """Check if action is idempotent and its effect already exists."""
        import os
        if action.action_type == ActionType.CREATE_FOLDER and action.target:
            path = self.entity_resolver.resolve(action.target)
            if path and os.path.exists(path) and os.path.isdir(path):
                return True
        return False