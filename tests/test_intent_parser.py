import pytest

from app.config.constants import AssistantMode, RiskLevel
from app.intelligence.intent_parser import IntentParser


def test_do_it_for_me_mode():
    parser = IntentParser()

    intent = parser.parse("Open Notepad")

    assert intent.mode == AssistantMode.DO_IT_FOR_ME
    assert intent.goal == "Open Notepad"


def test_show_me_how_mode():
    parser = IntentParser()

    intent = parser.parse("Show me how to open Notepad")

    assert intent.mode == AssistantMode.SHOW_ME_HOW
    assert intent.goal == "open Notepad"


def test_teach_me_mode():
    parser = IntentParser()

    intent = parser.parse("Teach me how to open Chrome")

    assert intent.mode == AssistantMode.SHOW_ME_HOW
    assert intent.goal == "open Chrome"


def test_high_risk_action():
    parser = IntentParser()

    intent = parser.parse("Delete this file")

    assert intent.risk_level == RiskLevel.HIGH
    assert intent.requires_confirmation is True


def test_normal_action_is_low_risk():
    parser = IntentParser()

    intent = parser.parse("Open Notepad")

    assert intent.risk_level == RiskLevel.LOW
    assert intent.requires_confirmation is False


def test_empty_input():
    parser = IntentParser()

    with pytest.raises(ValueError):
        parser.parse("")