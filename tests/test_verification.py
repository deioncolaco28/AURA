from unittest.mock import patch

from app.verification.application_verifier import (
    ApplicationVerifier,
)
from app.verification.verifier import (
    VerificationResult,
)


def test_verification_result_success():
    result = VerificationResult(
        success=True,
        message="Application is running.",
    )

    assert result.success is True
    assert bool(result) is True


def test_verification_result_failure():
    result = VerificationResult(
        success=False,
        message="Application is not running.",
    )

    assert result.success is False
    assert bool(result) is False


@patch(
    "app.verification.application_verifier.subprocess.run"
)
def test_application_is_running(mock_run):
    mock_run.return_value.stdout = (
        "Image Name                     PID\n"
        "notepad.exe                   1234\n"
    )

    verifier = ApplicationVerifier()

    result = verifier.verify("notepad.exe")

    assert result.success is True
    assert "running" in result.message.lower()


@patch(
    "app.verification.application_verifier.subprocess.run"
)
def test_application_is_not_running(mock_run):
    mock_run.return_value.stdout = (
        "INFO: No tasks are running.\n"
    )

    verifier = ApplicationVerifier()

    result = verifier.verify("notepad.exe")

    assert result.success is False
    assert "not running" in result.message.lower()


def test_empty_application_name():
    verifier = ApplicationVerifier()

    result = verifier.verify("")

    assert result.success is False