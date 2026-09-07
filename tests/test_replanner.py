from app.core.execution import ExecutionContext
from app.core.execution_engine import ExecutionEngine
from app.core.failure import FailureInfo
from app.core.observation import ScreenObservation
from app.core.replanner import (
    NoOpReplanner,
    Replanner,
)
from app.intelligence.action_factory import ActionFactory
from app.intelligence.task import Task


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

    failure = FailureInfo(
        action=action
    )

    result = replanner.replan(
        task=task,
        context=context,
        failed_action=action,
        observation=ScreenObservation(),
        failure=failure,
    )

    assert result == []


def test_replanner_is_abstract():
    try:
        Replanner()
        assert False, "Replanner should be abstract."
    except TypeError:
        pass


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
            failure,
        ):
            self.called = True

            assert failure.action is failed_action
            assert failure.error == (
                "Original failed"
            )

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

    assert context.metadata[
        "replan_count"
    ] == 1

    assert context.completed


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
            failure,
        ):
            self.calls += 1

            assert failure.action is failed_action
            assert failure.has_error

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

    assert context.metadata[
        "replan_count"
    ] == 1

    assert len(context.steps) == 2

    assert context.steps[0].status == "FAILED"
    assert context.steps[1].status == "FAILED"

    assert not context.completed