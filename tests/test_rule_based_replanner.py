from app.core.execution import ExecutionContext
from app.core.failure import FailureInfo
from app.core.observation import ScreenObservation
from app.core.rule_based_replanner import RuleBasedReplanner
from app.intelligence.action import ActionType
from app.intelligence.action_factory import ActionFactory
from app.intelligence.task import Task
from app.perception.ui_element import UIElement


def create_observation(elements):
    return ScreenObservation(
        screen_text="",
        elements=elements,
    )


def test_replanner_recovers_click_using_grounding():

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
                y=200,
                width=200,
                height=50,
            )
        ]
    )

    actions = replanner.replan(
        task=task,
        context=context,
        failed_action=failed_action,
        observation=observation,
    )

    assert len(actions) == 1

    action = actions[0]

    assert action.action_type == ActionType.CLICK
    assert action.target == "Notepad"
    assert action.resolved is True

    assert action.parameters["x"] == 200
    assert action.parameters["y"] == 225

    assert action.parameters["grounding_score"] >= 0.65

    assert action.metadata["recovery"] is True
    assert (
        action.metadata["recovery_strategy"]
        == "grounded_target"
    )


def test_replanner_recovers_double_click_using_grounding():

    replanner = RuleBasedReplanner()

    task = Task(
        goal="double click Notepad"
    )

    context = ExecutionContext(
        goal="double click Notepad",
        total_steps=1,
    )

    failed_action = ActionFactory.click(
        "Notepad"
    )

    failed_action.action_type = (
        ActionType.DOUBLE_CLICK
    )

    observation = create_observation(
        [
            UIElement(
                element_id="1",
                element_type="button",
                text="Notepad",
                x=50,
                y=50,
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
    )

    assert len(actions) == 1

    action = actions[0]

    assert (
        action.action_type
        == ActionType.DOUBLE_CLICK
    )

    assert action.target == "Notepad"
    assert action.resolved is True

    assert action.parameters["x"] == 100
    assert action.parameters["y"] == 70

    assert action.metadata["recovery"] is True


def test_replanner_does_not_recover_when_target_missing():

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
                width=150,
                height=50,
            )
        ]
    )

    actions = replanner.replan(
        task=task,
        context=context,
        failed_action=failed_action,
        observation=observation,
    )

    assert actions == []


def test_replanner_recovers_type_text_by_grounding_field():

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
                description="Search input",
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

    # Recovery should first focus the text field,
    # then type the requested text.
    assert len(actions) == 2

    click_action = actions[0]
    type_action = actions[1]

    assert click_action.action_type == ActionType.CLICK
    assert click_action.resolved is True

    assert click_action.parameters["x"] == 250
    assert click_action.parameters["y"] == 120

    assert (
        click_action.metadata["recovery_strategy"]
        == "grounded_text_field"
    )

    assert type_action.action_type == ActionType.TYPE_TEXT
    assert type_action.value == "Hello"

    assert (
        type_action.metadata["recovery_strategy"]
        == "grounded_text_field"
    )


def test_replanner_does_not_recover_type_text_without_text_field():

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
                element_type="button",
                text="Submit",
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
    )

    assert actions == []