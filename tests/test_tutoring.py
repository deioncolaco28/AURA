"""
Tests for the Tutor instruction generator.

Updated per spec §39: old overlay-dependent wording replaced with
semantic/spatial instructions that match the new Tutor implementation.
"""

from app.config.constants import AssistantMode
from app.intelligence.action import Action, ActionType
from app.intelligence.intent import Intent
from app.intelligence.planner import Planner
from app.tutoring.tutor import Tutor


def test_tutor_converts_speak_action():
    tutor = Tutor()

    action = Action(
        action_type=ActionType.SPEAK,
        value="I will help you.",
    )

    task = type(
        "TestTask",
        (),
        {"actions": [action]},
    )()

    instructions = tutor.create_instructions(task)

    assert len(instructions) == 1
    assert (
        instructions[0].message
        == "I will help you."
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

    instructions = tutor.create_instructions(task)

    assert len(instructions) == 1

    instruction = instructions[0]

    # New semantic message — no overlay-dependent wording.
    assert instruction.message == "Click Start."

    assert instruction.target == "Start"
    assert instruction.action_type == ActionType.CLICK

    # Completion condition is set (target_disappears or explicit verification).
    assert instruction.completion

    # expected_transition is set.
    assert instruction.expected_transition

    # Recovery is configured.
    assert instruction.recovery["max_attempts"] == 2


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

    instructions = tutor.create_instructions(task)

    assert len(instructions) == 1

    instruction = instructions[0]

    # Semantic message.
    assert "Hello World" in instruction.message
    assert instruction.action_type == ActionType.TYPE_TEXT
    assert instruction.parameters == {
        "text": "Hello World"
    }

    # expected_transition must require baseline comparison.
    assert instruction.expected_transition.get("requires_baseline")

    # Recovery configured.
    assert instruction.recovery["max_attempts"] == 2


def test_tutor_converts_windows_key_action():
    tutor = Tutor()

    action = Action(
        action_type=ActionType.PRESS_KEY,
        value="win",
    )

    task = type(
        "TestTask",
        (),
        {"actions": [action]},
    )()

    instructions = tutor.create_instructions(task)

    assert len(instructions) == 1

    instruction = instructions[0]

    # Must mention Windows key.
    assert "Windows" in instruction.message

    assert instruction.action_type == ActionType.PRESS_KEY
    assert instruction.parameters == {
        "key": "win"
    }
    assert instruction.completion == {
        "screen_changed": True
    }
    assert instruction.success_message is not None


def test_tutor_converts_planned_actions():
    planner = Planner()

    intent = Intent(
        raw_text="show me how to open notepad",
        goal="open notepad",
        mode=AssistantMode.SHOW_ME_HOW,
    )

    task = planner.create_task(intent)

    tutor = Tutor()

    instructions = tutor.create_instructions(task)

    # The planner produces 4 actions: SPEAK, PRESS_KEY, TYPE_TEXT, CLICK.
    assert len(instructions) == 4

    # Step 1: introductory voice guidance
    assert (
        instructions[0].action_type
        == ActionType.SPEAK
    )
    assert "Notepad" in instructions[0].message

    # Step 2: user presses Windows key
    assert (
        instructions[1].action_type
        == ActionType.PRESS_KEY
    )
    assert "Windows" in instructions[1].message
    assert instructions[1].completion == {
        "screen_changed": True
    }
    assert instructions[1].success_message is not None

    # Step 3: user types Notepad
    assert (
        instructions[2].action_type
        == ActionType.TYPE_TEXT
    )
    assert "Notepad" in instructions[2].message

    # expected_transition for TYPE_TEXT requires baseline.
    assert instructions[2].expected_transition.get("requires_baseline")

    # Step 4: user clicks Notepad — semantic click instruction.
    assert (
        instructions[3].action_type
        == ActionType.CLICK
    )

    # New semantic wording: "Click Notepad." (no overlay mention).
    assert instructions[3].message == "Click Notepad."

    assert instructions[3].target == "Notepad"

    # For Notepad click, the planner sets APPLICATION_RUNNING verification.
    assert (
        instructions[3].completion.get("type")
        == "APPLICATION_RUNNING"
    )

    # The planner may use 'process' or 'processes' depending on its schema.
    process_field = (
        instructions[3].completion.get("process")
        or (
            instructions[3].completion.get("processes", [None])[0]
            if instructions[3].completion.get("processes")
            else None
        )
    )
    assert process_field is not None
    assert "notepad" in str(process_field).lower()

    assert instructions[3].success_message is not None


def test_tutor_converts_launch_application_action():
    tutor = Tutor()

    action = Action(
        action_type=ActionType.LAUNCH_APPLICATION,
        target="Calculator",
    )

    task = type(
        "TestTask",
        (),
        {"actions": [action]},
    )()

    instructions = tutor.create_instructions(task)

    assert len(instructions) == 1

    instruction = instructions[0]

    assert "Calculator" in instruction.message
    assert instruction.target == "Calculator"

    # Completion specifies application_running.
    assert "application_running" in instruction.completion

    assert instruction.success_message is not None
    assert instruction.recovery["max_attempts"] == 2