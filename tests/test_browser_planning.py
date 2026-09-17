from app.config.constants import AssistantMode
from app.intelligence.action import ActionType
from app.intelligence.planner import Planner
from app.intelligence.intent import Intent


def test_planner_creates_browser_action():
    planner = Planner()

    intent = Intent(
        raw_text="open https://example.com",
        goal="open https://example.com",
        mode=AssistantMode.DO_IT_FOR_ME,
    )

    task = planner.create_task(intent)

    assert task.total_actions == 1

    assert (
        task.actions[0].action_type
        == ActionType.OPEN_URL
    )

    assert (
        task.actions[0].target
        == "https://example.com"
    )


def test_planner_detects_browser_action():
    planner = Planner()

    intent = Intent(
        raw_text="go to https://example.com",
        goal="go to https://example.com",
        mode=AssistantMode.DO_IT_FOR_ME,
    )

    task = planner.create_task(intent)

    assert len(task.actions) == 1

    assert (
        task.actions[0].action_type
        == ActionType.OPEN_URL
    )