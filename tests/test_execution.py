from app.core.execution import (
    ExecutionContext,
)
from app.core.execution_engine import (
    ExecutionEngine,
)
from app.intelligence.action_factory import (
    ActionFactory,
)
from app.intelligence.task import Task


def test_execution_context_tracks_completed_steps():
    context = ExecutionContext(
        goal="test task",
        total_steps=1,
    )

    action = ActionFactory.speak(
        "Hello"
    )

    step = context.add_step(
        action
    )

    assert step.index == 1
    assert step.status == "PENDING"

    context.mark_completed(
        step,
        verification={
            "success": True
        },
    )

    assert step.status == "COMPLETED"
    assert context.completed
    assert not context.failed


def test_execution_context_tracks_failed_steps():
    context = ExecutionContext(
        goal="test task",
        total_steps=1,
    )

    action = ActionFactory.speak(
        "Hello"
    )

    step = context.add_step(
        action
    )

    context.mark_failed(
        step,
        "Test failure",
    )

    assert step.status == "FAILED"
    assert step.error == "Test failure"
    assert context.failed
    assert not context.completed


def test_execution_engine_runs_actions_in_order():
    executed = []
    verified = []

    def execute_action(action):
        executed.append(
            action.value
        )

        action.execution_result = {
            "success": True
        }

        return action

    def verify_action(action):
        verified.append(
            action.value
        )

    engine = ExecutionEngine(
        execute_action=execute_action,
        verify_action=verify_action,
    )

    task = Task(
        goal="test sequence"
    )

    task.add_action(
        ActionFactory.speak(
            "First"
        )
    )

    task.add_action(
        ActionFactory.speak(
            "Second"
        )
    )

    context = engine.run(
        task
    )

    assert executed == [
        "First",
        "Second",
    ]

    assert verified == [
        "First",
        "Second",
    ]

    assert context.completed
    assert len(context.steps) == 2


def test_execution_engine_stops_after_exhausted_failure():
    executed = []

    def execute_action(action):
        executed.append(
            action.value
        )

        if action.value == "Fail":
            raise RuntimeError(
                "Intentional failure"
            )

        return action

    def verify_action(action):
        pass

    engine = ExecutionEngine(
        execute_action=execute_action,
        verify_action=verify_action,
        max_retries=1,
    )

    task = Task(
        goal="failure test"
    )

    task.add_action(
        ActionFactory.speak(
            "First"
        )
    )

    task.add_action(
        ActionFactory.speak(
            "Fail"
        )
    )

    task.add_action(
        ActionFactory.speak(
            "Should not execute"
        )
    )

    context = engine.run(
        task
    )

    assert executed == [
        "First",
        "Fail",
        "Fail",
    ]

    assert len(context.steps) == 2

    assert context.steps[0].status == "COMPLETED"

    assert context.steps[1].status == "FAILED"

    assert context.steps[1].attempts == 2

    assert context.steps[1].recovery_attempted

    assert context.steps[1].error == (
        "Intentional failure"
    )

    assert not context.completed
    assert context.failed


def test_execution_engine_recovers_from_transient_failure():
    attempts = []

    def execute_action(action):
        attempts.append(
            len(attempts) + 1
        )

        if len(attempts) == 1:
            raise RuntimeError(
                "Temporary failure"
            )

        action.execution_result = {
            "success": True
        }

        return action

    def verify_action(action):
        pass

    engine = ExecutionEngine(
        execute_action=execute_action,
        verify_action=verify_action,
        max_retries=1,
    )

    task = Task(
        goal="recovery test"
    )

    task.add_action(
        ActionFactory.speak(
            "Recover me"
        )
    )

    context = engine.run(
        task
    )

    assert attempts == [
        1,
        2,
    ]

    assert context.completed
    assert not context.failed

    assert context.steps[0].status == (
        "COMPLETED"
    )

    assert context.steps[0].attempts == 2
    assert context.steps[0].recovery_attempted