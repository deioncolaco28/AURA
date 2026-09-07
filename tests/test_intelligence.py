from app.config.constants import AssistantMode, RiskLevel
from app.intelligence.action import Action, ActionType
from app.intelligence.intent import Intent
from app.intelligence.mode_router import ModeRouter
from app.intelligence.planner import Planner
from app.intelligence.task import Task
from app.intelligence.action_factory import ActionFactory
from app.intelligence.task_decomposer import (
    RuleBasedTaskDecomposer,
)


def test_action_creation():
    action = Action(
        action_type=ActionType.LAUNCH_APPLICATION,
        target="Notepad",
    )

    assert action.action_type == ActionType.LAUNCH_APPLICATION
    assert action.target == "Notepad"


def test_task_creation():
    task = Task(
        goal="Open Notepad",
        mode=AssistantMode.DO_IT_FOR_ME,
        risk_level=RiskLevel.LOW,
    )

    assert task.goal == "Open Notepad"
    assert task.mode == AssistantMode.DO_IT_FOR_ME
    assert task.total_actions == 0


def test_add_action_to_task():
    task = Task(goal="Open Notepad")

    action = Action(
        action_type=ActionType.LAUNCH_APPLICATION,
        target="Notepad",
    )

    task.add_action(action)

    assert task.total_actions == 1
    assert task.actions[0].target == "Notepad"


def test_intent_creation():
    intent = Intent(
        raw_text="Show me how to open Notepad",
        goal="Open Notepad",
        mode=AssistantMode.SHOW_ME_HOW,
    )

    assert intent.mode == AssistantMode.SHOW_ME_HOW


def test_mode_router():
    intent = Intent(
        raw_text="Show me how to open Notepad",
        goal="Open Notepad",
        mode=AssistantMode.SHOW_ME_HOW,
    )

    router = ModeRouter()

    assert router.route(intent) == AssistantMode.SHOW_ME_HOW


def test_planner_creates_task():
    intent = Intent(
        raw_text="Open Notepad",
        goal="Open Notepad",
    )

    planner = Planner()
    task = planner.create_task(intent)

    assert isinstance(task, Task)
    assert task.goal == "Open Notepad"


def test_planner_creates_launch_application_action():
    intent = Intent(
        raw_text="Open Notepad",
        goal="Open Notepad",
    )

    planner = Planner()
    task = planner.create_task(intent)

    assert task.total_actions == 1
    assert (
        task.actions[0].action_type
        == ActionType.LAUNCH_APPLICATION
    )
    assert task.actions[0].target == "notepad"


def test_planner_creates_multi_step_notepad_task():
    intent = Intent(
        raw_text="Open Notepad and type Hello World",
        goal="Open Notepad and type Hello World",
    )

    planner = Planner()

    task = planner.create_task(intent)

    assert task.total_actions == 2

    assert (
        task.actions[0].action_type
        == ActionType.LAUNCH_APPLICATION
    )

    assert (
        task.actions[1].action_type
        == ActionType.TYPE_TEXT
    )

    assert task.actions[1].value == "Hello World"


def test_planner_creates_multi_step_notepad_task():
    planner = Planner()

    intent = Intent(
        raw_text="open notepad and type hello world",
        goal="open notepad and type hello world",
        mode=AssistantMode.DO_IT_FOR_ME,
    )

    task = planner.create_task(intent)

    assert task.total_actions == 2

    assert (
        task.actions[0].action_type
        == ActionType.LAUNCH_APPLICATION
    )

    assert (
        task.actions[0].target
        == "notepad"
    )

    assert (
        task.actions[1].action_type
        == ActionType.TYPE_TEXT
    )

    assert (
        task.actions[1].value
        == "Hello World"
    )


def test_planner_adds_screen_text_verification():
    planner = Planner()

    intent = Intent(
        raw_text="open notepad and type hello world",
        goal="open notepad and type hello world",
    )

    task = planner.create_task(intent)

    verification = (
        task.actions[1].verification
    )

    assert (
        verification["type"]
        == "SCREEN_CONTAINS_TEXT"
    )

    assert (
        verification["text"]
        == "Hello World"
    )


def test_rule_based_task_decomposer_creates_multi_step_task():
    decomposer = RuleBasedTaskDecomposer()

    actions = decomposer.decompose(
        "open notepad and type hello world"
    )

    assert len(actions) == 2

    assert (
        actions[0].action_type
        == ActionType.LAUNCH_APPLICATION
    )

    assert (
        actions[1].action_type
        == ActionType.TYPE_TEXT
    )

    assert actions[1].value == "Hello World"


def test_planner_uses_injected_task_decomposer():
    class FakeDecomposer:
        def decompose(
            self,
            goal,
            mode,
        ):
            return [
                ActionFactory.speak(
                    "Fake planned action."
                )
            ]

    planner = Planner(
        decomposer=FakeDecomposer()
    )

    intent = Intent(
        raw_text="do something",
        goal="do something",
    )

    task = planner.create_task(
        intent
    )

    assert task.total_actions == 1

    assert (
        task.actions[0].action_type
        == ActionType.SPEAK
    )

    assert (
        task.actions[0].value
        == "Fake planned action."
    )


def test_rule_based_decomposer_supports_show_me_how():
    decomposer = RuleBasedTaskDecomposer()

    actions = decomposer.decompose(
        "open notepad",
        mode=AssistantMode.SHOW_ME_HOW,
    )

    assert len(actions) == 4

    assert (
        actions[0].action_type
        == ActionType.SPEAK
    )

    assert (
        actions[1].action_type
        == ActionType.PRESS_KEY
    )

    assert (
        actions[2].action_type
        == ActionType.TYPE_TEXT
    )

    assert (
        actions[3].action_type
        == ActionType.CLICK
    )


def test_show_me_how_type_action_has_text_verification():
    decomposer = RuleBasedTaskDecomposer()

    actions = decomposer.decompose(
        "open notepad",
        mode=AssistantMode.SHOW_ME_HOW,
    )

    verification = (
        actions[2].verification
    )

    assert (
        verification["type"]
        == "SCREEN_CONTAINS_TEXT"
    )

    assert (
        verification["text"]
        == "Notepad"
    )