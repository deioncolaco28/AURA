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

    assert (
        instruction.message
        == (
            "Excellent. I found Start and highlighted it. "
            "Now click it to continue."
        )
    )

    assert instruction.target == "Start"
    assert instruction.action_type == ActionType.CLICK
    assert instruction.completion == {
        "target_disappears": "Start"
    }
    assert instruction.success_message == (
        "Perfect. Start has been opened."
    )
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

    assert (
        instruction.message
        == (
            "Great. Now type 'Hello World' into the "
            "search box. I'll let you know when I can see it."
        )
    )

    assert instruction.action_type == ActionType.TYPE_TEXT
    assert instruction.parameters == {
        "text": "Hello World"
    }
    assert instruction.completion == {
        "screen_contains": "Hello World"
    }
    assert instruction.success_message == (
        "Perfect. I can see 'Hello World' on the screen."
    )
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

    assert (
        instruction.message
        == (
            "First, press the Windows key. "
            "I'll wait for the Start menu to appear."
        )
    )

    assert instruction.action_type == ActionType.PRESS_KEY
    assert instruction.parameters == {
        "key": "win"
    }
    assert instruction.completion == {
        "screen_changed": True
    }
    assert instruction.success_message == (
        "Good. I can see that the screen changed."
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

    instructions = tutor.create_instructions(task)

    assert len(instructions) == 4

    # Step 1: introductory voice guidance
    assert (
        instructions[0].message
        == "I will show you how to open Notepad."
    )

    # Step 2: user presses Windows key
    assert (
        instructions[1].message
        == (
            "First, press the Windows key. "
            "I'll wait for the Start menu to appear."
        )
    )

    assert instructions[1].completion == {
        "screen_changed": True
    }

    assert instructions[1].success_message == (
        "Good. I can see that the screen changed."
    )

    # Step 3: user types Notepad
    assert (
        instructions[2].message
        == (
            "Great. Now type 'Notepad' into the "
            "search box. I'll let you know when I can see it."
        )
    )

    assert instructions[2].completion == {
        "screen_contains": "Notepad"
    }

    # Step 4: user clicks Notepad
    assert (
        instructions[3].message
        == (
            "Excellent. I found Notepad and highlighted it. "
            "Now click it to continue."
        )
    )

    assert instructions[3].target == "Notepad"
    assert (
        instructions[3].completion["type"]
        == "APPLICATION_RUNNING"
    )

    assert (
        instructions[3].completion["process"]
        == "notepad.exe"
    )

    assert instructions[3].success_message == (
        "Perfect. Notepad has been opened."
    )


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

    assert (
        instruction.message
        == (
            "Please open Calculator. "
            "I'll wait and confirm when it is running."
        )
    )

    assert instruction.target == "Calculator"

    assert instruction.completion == {
        "application_running": "Calculator.exe"
    }

    assert instruction.success_message == (
        "Perfect. Calculator is now open."
    )

    assert instruction.recovery["max_attempts"] == 2