from app.core.execution import ExecutionContext
from app.core.observation import ScreenObservation
from app.core.rule_based_replanner import (
    RuleBasedReplanner,
)
from app.intelligence.action import (
    Action,
    ActionType,
)
from app.intelligence.action_factory import (
    ActionFactory,
)
from app.intelligence.task import Task
from app.perception.ui_element import UIElement
from app.core.failure import FailureInfo


def create_observation(
    elements,
):
    return ScreenObservation(
        elements=elements
    )


def test_replanner_recovers_click_when_target_exists():

    replanner = RuleBasedReplanner()

    task = Task(
        goal="click Notepad"
    )

    context = ExecutionContext(
        goal="click Notepad",
        total_steps=1,
    )

    failed_action = ActionFactory.click(
        "Notepad"
    )

    observation = create_observation(
        [
            UIElement(
                element_id="1",
                element_type="button",
                text="Notepad",
                x=100,
                y=100,
                width=100,
                height=40,
            )
        ]
    )

    actions = replanner.replan(
        task=task,
        context=context,
        failed_action=failed_action,
        observation=observation,
        failure=FailureInfo(
            action=failed_action
        ),
    )

    assert len(actions) == 1

    replacement = actions[0]

    assert (
        replacement.action_type
        == ActionType.CLICK
    )

    assert replacement.target == "Notepad"

    assert replacement.resolved

    assert replacement.parameters["x"] == 150
    assert replacement.parameters["y"] == 120

    assert (
        replacement.parameters[
            "grounding_score"
        ]
        >= 0.65
    )

    assert (
        replacement.metadata[
            "recovery"
        ]
        is True
    )


def test_replanner_returns_nothing_when_target_missing():

    replanner = RuleBasedReplanner()

    task = Task(
        goal="click Notepad"
    )

    context = ExecutionContext(
        goal="click Notepad",
        total_steps=1,
    )

    failed_action = ActionFactory.click(
        "Notepad"
    )

    observation = create_observation(
        [
            UIElement(
                element_id="1",
                element_type="button",
                text="Calculator",
                x=100,
                y=100,
                width=100,
                height=40,
            )
        ]
    )

    actions = replanner.replan(
        task=task,
        context=context,
        failed_action=failed_action,
        observation=observation,
        failure=FailureInfo(
            action=failed_action
        ),
    )

    assert actions == []


def test_replanner_recovers_double_click():

    replanner = RuleBasedReplanner()

    task = Task(
        goal="open file"
    )

    context = ExecutionContext(
        goal="open file",
        total_steps=1,
    )

    failed_action = Action(
        action_type=ActionType.DOUBLE_CLICK,
        target="Document",
    )

    observation = create_observation(
        [
            UIElement(
                element_id="1",
                element_type="file",
                text="Document",
                x=200,
                y=200,
                width=120,
                height=40,
            )
        ]
    )

    actions = replanner.replan(
        task=task,
        context=context,
        failed_action=failed_action,
        observation=observation,
        failure=FailureInfo(
            action=failed_action
        ),
    )

    assert len(actions) == 1

    replacement = actions[0]

    assert (
        replacement.action_type
        == ActionType.DOUBLE_CLICK
    )

    assert replacement.resolved

    assert replacement.parameters["x"] == 260
    assert replacement.parameters["y"] == 220


def test_replanner_recovers_type_text_when_screen_has_elements():

    replanner = RuleBasedReplanner()

    task = Task(
        goal="type Hello"
    )

    context = ExecutionContext(
        goal="type Hello",
        total_steps=1,
    )

    failed_action = ActionFactory.type_text(
        "Hello"
    )

    observation = create_observation(
        [
            UIElement(
                element_id="1",
                element_type="text_field",
                text="",
                x=100,
                y=100,
                width=300,
                height=40,
            )
        ]
    )

    actions = replanner.replan(
        task=task,
        context=context,
        failed_action=failed_action,
        observation=observation,
        failure=FailureInfo(
            action=failed_action
        ),
    )

    assert len(actions) == 1

    replacement = actions[0]

    assert (
        replacement.action_type
        == ActionType.TYPE_TEXT
    )

    assert replacement.value == "Hello"

    assert (
        replacement.metadata[
            "recovery"
        ]
        is True
    )


def test_replanner_stops_when_observation_failed():

    replanner = RuleBasedReplanner()

    task = Task(
        goal="click Notepad"
    )

    context = ExecutionContext(
        goal="click Notepad",
        total_steps=1,
    )

    failed_action = ActionFactory.click(
        "Notepad"
    )

    observation = ScreenObservation(
        metadata={
            "observation_failed": True
        }
    )

    actions = replanner.replan(
        task=task,
        context=context,
        failed_action=failed_action,
        observation=observation,
        failure=FailureInfo(
            action=failed_action
        ),
    )

    assert actions == []