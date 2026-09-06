from unittest.mock import Mock

from app.automation.action_executor import ActionExecutor
from app.core.agent import Agent
from app.intelligence.planner import Planner
from app.voice.voice_manager import VoiceManager


def test_agent_process_text():
    voice_manager = Mock(spec=VoiceManager)
    action_executor = Mock(spec=ActionExecutor)

    agent = Agent(
        voice_manager=voice_manager,
        planner=Planner(),
        action_executor=action_executor,
    )

    agent.process_text("Open Notepad")

    action_executor.execute.assert_called_once()

    voice_manager.speak.assert_called()