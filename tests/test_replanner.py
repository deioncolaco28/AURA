from app.core.execution import (
    ExecutionContext,
)
from app.core.execution_engine import (
    ExecutionEngine,
)
from app.core.replanner import (
    NoOpReplanner,
    Replanner,
)
from app.intelligence.action import (
    Action,
)
from app.intelligence.action_factory import (
    ActionFactory,
)
from app.intelligence.task import (
    Task,
)
from app.core.observation import ScreenObservation


def test_noop_replanner_returns_no_actions():
    replanner = NoOpReplanner()

    task = Task(
        goal="test"
    )

    context = ExecutionContext(
        goal="test",
        total_steps=1,
    )

    action = ActionFactory.speak(
        "Fail"
    )

    result = replanner.replan(
        task=task,
        context=context,
        failed_action=action,
        observation=ScreenObservation(),
    )

    assert result == []


def test_execution_engine_can_use_replanner():
    class FakeReplanner(Replanner):

        def __init__(self):
            self.called = False

        def replan(
            self,
            task,
            context,
            failed_action,
            observation,
        ):
            self.called = True

            return [
                ActionFactory.speak(
                    "Replacement"
                )
            ]

    executed = []
    replanner = FakeReplanner()

    def execute_action(action):
        executed.append(
            action.value
        )

        if action.value == "Original":
            raise RuntimeError(
                "Original failed"
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
        max_retries=0,
        replanner=replanner,
        max_replans=1,
    )

    task = Task(
        goal="replan test"
    )

    task.add_action(
        ActionFactory.speak(
            "Original"
        )
    )

    context = engine.run(
        task
    )

    assert replanner.called

    assert executed == [
        "Original",
        "Replacement",
    ]

    assert context.steps[0].status == (
        "FAILED"
    )

    assert context.steps[1].status == (
        "COMPLETED"
    )

    assert context.completed

    assert context.metadata[
        "replan_count"
    ] == 1


def test_execution_engine_does_not_replan_after_success():
    class FakeReplanner(Replanner):

        def __init__(self):
            self.called = False

        def replan(
            self,
            task,
            context,
            failed_action,
            observation,
        ):
            self.called = True
            return [
                ActionFactory.speak(
                    "Should not run"
                )
            ]

    replanner = FakeReplanner()
    executed = []

    def execute_action(action):
        executed.append(
            action.value
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
        max_retries=0,
        replanner=replanner,
        max_replans=1,
    )

    task = Task(
        goal="success test"
    )

    task.add_action(
        ActionFactory.speak(
            "Success"
        )
    )

    context = engine.run(
        task
    )

    assert context.completed
    assert not replanner.called

    assert executed == [
        "Success"
    ]


def test_execution_engine_limits_replanning():
    class FakeReplanner(Replanner):

        def __init__(self):
            self.calls = 0

        def replan(
            self,
            task,
            context,
            failed_action,
            observation,
        ):
            self.calls += 1

            return [
                ActionFactory.speak(
                    "Still failing"
                )
            ]

    replanner = FakeReplanner()

    def execute_action(action):
        raise RuntimeError(
            "Always fails"
        )

    def verify_action(action):
        pass

    engine = ExecutionEngine(
        execute_action=execute_action,
        verify_action=verify_action,
        max_retries=0,
        replanner=replanner,
        max_replans=1,
    )

    task = Task(
        goal="limit test"
    )

    task.add_action(
        ActionFactory.speak(
            "Initial"
        )
    )

    context = engine.run(
        task
    )

    assert replanner.calls == 1

    assert context.failed
    assert not context.completed

    assert context.metadata[
        "replan_count"
    ] == 1