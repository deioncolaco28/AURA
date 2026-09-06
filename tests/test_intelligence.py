from app.config.constants import AssistantMode, RiskLevel
from app.intelligence.action import Action, ActionType
from app.intelligence.intent import Intent
from app.intelligence.mode_router import ModeRouter
from app.intelligence.planner import Planner
from app.intelligence.task import Task


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