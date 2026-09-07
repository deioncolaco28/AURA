from unittest.mock import Mock

from app.config.constants import AssistantMode
from app.intelligence.action import Action, ActionType
from app.intelligence.intent import Intent
from app.intelligence.planner import Planner
from app.tutoring.instruction import TutoringInstruction
from app.tutoring.tutor import Tutor
from app.tutoring.tutoring_controller import (
    TutoringController,
)


def test_tutoring_instruction_creation():
    instruction = TutoringInstruction(
        message="Click Start.",
        target="Start",
        action_type=ActionType.CLICK,
        completion={
            "screen_contains": "Start"
        },
    )

    assert instruction.message == "Click Start."
    assert instruction.target == "Start"
    assert instruction.action_type == ActionType.CLICK
    assert instruction.completed is False
    assert (
        instruction.completion[
            "screen_contains"
        ]
        == "Start"
    )


def test_tutor_converts_click_action():
    tutor = Tutor()

    action = Action(
        action_type=ActionType.CLICK,
        target="Start",
    )

    task = type(
        "TestTask",
        (),
        {"actions": [action]},
    )()

    instructions = tutor.create_instructions(
        task
    )

    assert len(instructions) == 1
    assert (
        instructions[0].message
        == "Click the highlighted Start."
    )
    assert instructions[0].target == "Start"
    assert (
        instructions[0].action_type
        == "CLICK"
    )


def test_tutor_converts_type_action():
    tutor = Tutor()

    action = Action(
        action_type=ActionType.TYPE_TEXT,
        value="Hello World",
    )

    task = type(
        "TestTask",
        (),
        {"actions": [action]},
    )()

    instructions = tutor.create_instructions(
        task
    )

    assert len(instructions) == 1
    assert (
        instructions[0].message
        == "Type Hello World."
    )
    assert (
        instructions[0].action_type
        == "TYPE_TEXT"
    )
    assert (
        instructions[0].completion[
            "screen_contains"
        ]
        == "Hello World"
    )


def test_tutor_converts_planned_actions():
    planner = Planner()

    intent = Intent(
        raw_text="show me how to open notepad",
        goal="open notepad",
        mode=AssistantMode.SHOW_ME_HOW,
    )

    task = planner.create_task(intent)

    tutor = Tutor()

    instructions = tutor.create_instructions(
        task
    )

    assert len(instructions) == 4

    assert (
        instructions[0].message
        == "I will show you how to open Notepad."
    )

    assert (
        instructions[1].message
        == "Press the Windows key."
    )

    assert (
        instructions[1].completion[
            "screen_changed"
        ]
        is True
    )

    assert (
        instructions[2].message
        == "Type Notepad."
    )

    assert (
        instructions[2].completion[
            "screen_contains"
        ]
        == "Notepad"
    )

    assert (
        instructions[3].message
        == "Click the highlighted Notepad."
    )


def test_tutoring_controller_runs_instructions():
    voice_manager = Mock()

    controller = TutoringController(
        voice_manager=voice_manager
    )

    controller._wait_for_completion = Mock(
        return_value=True
    )

    instructions = [
        TutoringInstruction(
            message="Press the Windows key.",
            action_type=ActionType.PRESS_KEY,
            completion={
                "screen_contains": "Notepad"
            },
        ),
        TutoringInstruction(
            message="Type Notepad.",
            action_type=ActionType.TYPE_TEXT,
            completion={
                "screen_contains": "Notepad"
            },
        ),
    ]

    controller.run(
        instructions
    )

    assert (
        voice_manager.speak.call_count
        == 2
    )

    assert (
        voice_manager.speak.call_args_list[0]
        .args[0]
        == "Press the Windows key."
    )

    assert (
        voice_manager.speak.call_args_list[1]
        .args[0]
        == "Type Notepad."
    )

    assert (
        controller._wait_for_completion.call_count
        == 2
    )

    assert instructions[0].completed is True
    assert instructions[1].completed is True