from app.automation.browser import BrowserController


def test_browser_controller_initial_state():
    browser = BrowserController(headless=True)

    assert browser.page is None
    assert browser.browser is None
    assert browser.playwright is None


def test_browser_open_url():
    browser = BrowserController(headless=True)

    result = browser.open_url(
        "data:text/html,<html><title>AURA Test</title>"
        "<body>Hello AURA</body></html>"
    )

    assert result.success is True
    assert "AURA Test" == browser.get_title()

    browser.close()


def test_browser_close():
    browser = BrowserController(headless=True)

    browser.open_url(
        "data:text/html,<html><body>AURA</body></html>"
    )

    browser.close()

    assert browser.page is None
    assert browser.browser is None
    assert browser.playwright is None