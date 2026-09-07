from app.core.failure import (
    FailureInfo,
    FailureType,
)
from app.intelligence.action_factory import (
    ActionFactory,
)


def test_failure_info_defaults_to_unknown():
    action = ActionFactory.speak(
        "Test"
    )

    failure = FailureInfo(
        action=action
    )

    assert failure.failure_type == (
        FailureType.UNKNOWN
    )

    assert not failure.has_error
    assert not failure.is_execution_failure
    assert not failure.is_verification_failure


def test_failure_info_detects_execution_failure():
    action = ActionFactory.speak(
        "Test"
    )

    failure = FailureInfo(
        action=action,
        error="Click failed",
        failure_type=FailureType.EXECUTION,
    )

    assert failure.has_error
    assert failure.is_execution_failure
    assert not failure.is_verification_failure


def test_failure_info_detects_verification_failure():
    action = ActionFactory.launch_application(
        "notepad",
        verification={
            "type": "APPLICATION_RUNNING",
            "process": "notepad.exe",
        },
    )

    failure = FailureInfo(
        action=action,
        error="Application was not detected.",
        verification=action.verification,
        failure_type=FailureType.VERIFICATION,
    )

    assert failure.has_error
    assert failure.verification_type == (
        "APPLICATION_RUNNING"
    )

    assert failure.is_verification_failure
    assert not failure.is_execution_failure