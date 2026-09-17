from app.automation.action_executor import ActionExecutor
from app.automation.browser import BrowserController
from app.intelligence.action import Action, ActionType


def test_open_url_action():
    browser = BrowserController(
        headless=True
    )

    executor = ActionExecutor(
        browser_controller=browser
    )

    action = Action(
        action_type=ActionType.OPEN_URL,
        target=(
            "data:text/html,"
            "<html>"
            "<head><title>AURA Browser Test</title></head>"
            "<body>AURA</body>"
            "</html>"
        ),
    )

    executor.execute(action)

    assert action.execution_result[
        "browser_success"
    ] is True

    assert (
        browser.get_title()
        == "AURA Browser Test"
    )

    browser.close()


def test_open_url_requires_target():
    browser = BrowserController(
        headless=True
    )

    executor = ActionExecutor(
        browser_controller=browser
    )

    action = Action(
        action_type=ActionType.OPEN_URL
    )

    try:
        executor.execute(action)
        assert False, (
            "OPEN_URL should require a target."
        )
    except ValueError as error:
        assert (
            str(error)
            == "OPEN_URL requires a target."
        )

    browser.close()