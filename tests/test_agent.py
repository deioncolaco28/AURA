from unittest.mock import Mock

from app.automation.action_executor import ActionExecutor
from app.core.agent import Agent
from app.intelligence.planner import Planner
from app.verification.application_verifier import (
    ApplicationVerifier,
)
from app.verification.verifier import VerificationResult
from app.voice.voice_manager import VoiceManager


def test_agent_process_text():
    voice_manager = Mock(spec=VoiceManager)
    action_executor = Mock(spec=ActionExecutor)
    application_verifier = Mock(spec=ApplicationVerifier)

    application_verifier.verify.return_value = VerificationResult(
        success=True,
        message="notepad.exe is running.",
    )

    agent = Agent(
        voice_manager=voice_manager,
        planner=Planner(),
        action_executor=action_executor,
        application_verifier=application_verifier,
    )

    agent.process_text("Open Notepad")

    action_executor.execute.assert_called_once()

    application_verifier.verify.assert_called_once_with(
        "notepad.exe"
    )

    voice_manager.speak.assert_called_with(
        "Task completed."
    )


def test_agent_retries_failed_verification():
    voice_manager = Mock(spec=VoiceManager)
    action_executor = Mock(spec=ActionExecutor)
    application_verifier = Mock(spec=ApplicationVerifier)

    application_verifier.verify.side_effect = [
        VerificationResult(
            success=False,
            message="notepad.exe is not running.",
        ),
        VerificationResult(
            success=False,
            message="notepad.exe is not running.",
        ),
        VerificationResult(
            success=True,
            message="notepad.exe is running.",
        ),
    ]

    agent = Agent(
        voice_manager=voice_manager,
        planner=Planner(),
        action_executor=action_executor,
        application_verifier=application_verifier,
    )

    agent.process_text("Open Notepad")

    assert application_verifier.verify.call_count == 3

    voice_manager.speak.assert_called_with(
        "Task completed."
    )


def test_agent_handles_verification_failure():
    voice_manager = Mock(spec=VoiceManager)
    action_executor = Mock(spec=ActionExecutor)
    application_verifier = Mock(spec=ApplicationVerifier)

    application_verifier.verify.return_value = (
        VerificationResult(
            success=False,
            message="notepad.exe is not running.",
        )
    )

    agent = Agent(
        voice_manager=voice_manager,
        planner=Planner(),
        action_executor=action_executor,
        application_verifier=application_verifier,
    )

    agent.process_text("Open Notepad")

    assert application_verifier.verify.call_count == 6

    voice_manager.speak.assert_called_with(
        "I could not complete that task."
    )


def test_agent_processes_multi_step_task():
    voice_manager = Mock(spec=VoiceManager)
    action_executor = Mock(spec=ActionExecutor)
    application_verifier = Mock(spec=ApplicationVerifier)

    application_verifier.verify.return_value = (
        VerificationResult(
            success=True,
            message="notepad.exe is running.",
        )
    )

    agent = Agent(
        voice_manager=voice_manager,
        planner=Planner(),
        action_executor=action_executor,
        application_verifier=application_verifier,
    )

    agent.process_text(
        "Open Notepad and type Hello World"
    )

    assert action_executor.execute.call_count == 2

    assert (
        application_verifier.verify.call_count == 1
    )

    voice_manager.speak.assert_called_with(
        "Task completed."
    )