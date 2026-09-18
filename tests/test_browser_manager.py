"""
Tests for BrowserManager and expanded BrowserController.
"""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from app.automation.browser import BrowserController, BrowserResult
from app.automation.browser_manager import BrowserManager


class TestBrowserManager:
    def setup_method(self):
        self.mock_ctrl = MagicMock(spec=BrowserController)
        self.mock_pm = MagicMock()
        self.bm = BrowserManager(controller=self.mock_ctrl, perception_manager=self.mock_pm)

    def test_navigation_and_url(self):
        self.mock_ctrl.navigate.return_value = BrowserResult(success=True, url="https://example.com")
        self.mock_ctrl.get_url.return_value = "https://example.com/page1"
        self.mock_ctrl.get_title.return_value = "Example Domain"

        res = self.bm.navigate("https://example.com")
        assert res.success is True
        assert self.bm.get_current_url() == "https://example.com/page1"
        assert self.bm.get_current_title() == "Example Domain"

    def test_dom_click_and_type(self):
        self.bm.click("button#submit")
        self.mock_ctrl.click.assert_called_once_with("button#submit")

        self.bm.type_text("input#search", "AURA Agent")
        self.mock_ctrl.type_text.assert_called_once_with("input#search", "AURA Agent")

    def test_tab_operations(self):
        self.bm.open_tab("https://google.com")
        self.mock_ctrl.open_tab.assert_called_once_with("https://google.com")

        self.bm.switch_tab(1)
        self.mock_ctrl.switch_tab.assert_called_once_with(1)

        self.bm.close_tab(0)
        self.mock_ctrl.close_tab.assert_called_once_with(0)

    def test_wait_for_url_contains_polling(self):
        # Sequence of URLs changing to target
        self.mock_ctrl.get_url.side_effect = [
            "https://login.example.com",
            "https://login.example.com/auth",
            "https://dashboard.example.com",
        ]

        found = self.bm.wait_for_url_contains("dashboard", timeout_sec=1.0, poll_interval=0.01)
        assert found is True

    def test_wait_for_title_contains_polling(self):
        self.mock_ctrl.get_title.side_effect = [
            "Loading...",
            "Welcome to AURA",
        ]

        found = self.bm.wait_for_title_contains("Welcome", timeout_sec=1.0, poll_interval=0.01)
        assert found is True
