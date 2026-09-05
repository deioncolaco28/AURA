from app.config.constants import AssistantState
from app.core.assistant import Assistant


def test_assistant_initial_state():
    assistant = Assistant()

    assert assistant.state.current_state == AssistantState.IDLE


def test_assistant_start():
    assistant = Assistant()

    assistant.start()

    assert assistant.state.current_state == AssistantState.IDLE


def test_assistant_stop():
    assistant = Assistant()

    assistant.start()
    assistant.stop()

    assert assistant.state.current_state == AssistantState.IDLE


def test_get_state():
    assistant = Assistant()

    state = assistant.get_state()

    assert state is assistant.state