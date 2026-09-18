"""
app/core/failure.py

Central structured failure taxonomy and deterministic failure classifier for AURA.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.intelligence.action import Action


class FailureType:
    """Comprehensive taxonomy of failure types during agent computer-use tasks."""

    # Perception & Target Grounding
    TARGET_NOT_FOUND = "TARGET_NOT_FOUND"
    TARGET_AMBIGUOUS = "TARGET_AMBIGUOUS"
    TARGET_MOVED = "TARGET_MOVED"
    TARGET_NOT_INTERACTABLE = "TARGET_NOT_INTERACTABLE"
    PERCEPTION_UNAVAILABLE = "PERCEPTION_UNAVAILABLE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    SCROLL_LIMIT_REACHED = "SCROLL_LIMIT_REACHED"

    # Application & Window
    APPLICATION_NOT_RUNNING = "APPLICATION_NOT_RUNNING"
    APPLICATION_NOT_FOREGROUND = "APPLICATION_NOT_FOREGROUND"
    APPLICATION_CRASHED = "APPLICATION_CRASHED"

    # Verification & State
    EXPECTED_STATE_NOT_REACHED = "EXPECTED_STATE_NOT_REACHED"
    UNEXPECTED_STATE = "UNEXPECTED_STATE"
    VERIFICATION = "VERIFICATION_FAILURE"

    # Content Intelligence
    CONTENT_NOT_FOUND = "CONTENT_NOT_FOUND"
    CONTENT_UNREADABLE = "CONTENT_UNREADABLE"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    OCR_FAILED = "OCR_FAILED"
    DOCUMENT_CORRUPTED = "DOCUMENT_CORRUPTED"
    WORKBOOK_ERROR = "WORKBOOK_ERROR"
    PRESENTATION_ERROR = "PRESENTATION_ERROR"
    WEB_CONTENT_UNAVAILABLE = "WEB_CONTENT_UNAVAILABLE"
    INSUFFICIENT_CONTENT = "INSUFFICIENT_CONTENT"
    CONTENT_OPERATION_FAILED = "CONTENT_OPERATION_FAILED"
    OUTPUT_VALIDATION_FAILED = "OUTPUT_VALIDATION_FAILED"

    # Execution & System
    ACTION_FAILED = "ACTION_FAILED"
    EXECUTION = "EXECUTION_FAILURE"
    TIMEOUT = "TIMEOUT"
    PERMISSION_REQUIRED = "PERMISSION_REQUIRED"
    NETWORK_FAILURE = "NETWORK_FAILURE"
    FILESYSTEM = "FILESYSTEM_FAILURE"
    FILESYSTEM_ERROR = "FILESYSTEM_FAILURE"
    BROWSER_ERROR = "BROWSER_ERROR"
    DEPENDENCY_FAILED = "DEPENDENCY_FAILED"
    UNKNOWN = "UNKNOWN_FAILURE"
    UNKNOWN_FAILURE = "UNKNOWN_FAILURE"


@dataclass
class FailureInfo:
    """Structured information describing why an action or task node failed."""

    action: Action
    error: str | None = None
    verification: dict[str, Any] = field(default_factory=dict)
    attempt: int = 0
    failure_type: str = FailureType.UNKNOWN
    task_id: str | None = None
    environment: str | None = None
    observed_state: Any = None
    expected_state: Any = None
    explanation: str = ""
    recoverability: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def has_error(self) -> bool:
        """Return True when an execution error exists."""
        return bool(self.error and self.error.strip())

    @property
    def verification_type(self) -> str | None:
        """Return the configured verification type."""
        value = self.verification.get("type")
        if value is None:
            return None
        return str(value)

    @property
    def is_execution_failure(self) -> bool:
        """Return True when execution itself failed."""
        return self.failure_type in (FailureType.EXECUTION, FailureType.ACTION_FAILED)

    @property
    def is_verification_failure(self) -> bool:
        """Return True when verification failed."""
        return self.failure_type in (FailureType.VERIFICATION, FailureType.EXPECTED_STATE_NOT_REACHED)


class FailureClassifier:
    """
    Deterministic classifier that analyzes execution errors, state comparisons,
    and observation diffs to produce structured FailureInfo with recovery hints.
    """

    def classify(
        self,
        action: Action,
        error: str | None = None,
        verification_result: Any = None,
        comparison_result: Any = None,
        diff: Any = None,
        observation: Any = None,
        attempt: int = 1,
        task_id: str | None = None,
        environment: str | None = None,
    ) -> FailureInfo:
        """Classify a failure into a canonical FailureType."""
        err_str = str(error or "").lower()
        explanation = str(error or "")
        recoverable = True

        # 1. Non-retryable programming / syntax / system errors
        if any(
            err_marker in err_str
            for err_marker in (
                "nameerror",
                "typeerror",
                "syntaxerror",
                "importerror",
                "modulenotfounderror",
                "attributeerror",
                "valueerror",
                "name '",
                "not defined",
                "invalid syntax",
                "unsupported executable action",
            )
        ):
            ftype = FailureType.ACTION_FAILED
            recoverable = False
        # 2. Check explicit error message patterns
        elif "ambiguous" in err_str:
            ftype = FailureType.TARGET_AMBIGUOUS
            recoverable = False
        elif "permission" in err_str or "access denied" in err_str or "unauthorized" in err_str:
            ftype = FailureType.PERMISSION_REQUIRED
            recoverable = False
        elif "not running" in err_str:
            ftype = FailureType.APPLICATION_NOT_RUNNING
        elif "not in the foreground" in err_str or "not foreground" in err_str:
            ftype = FailureType.APPLICATION_NOT_FOREGROUND
        elif "crashed" in err_str or "terminated unexpectedly" in err_str:
            ftype = FailureType.APPLICATION_CRASHED
        elif "timeout" in err_str or "timed out" in err_str:
            ftype = FailureType.TIMEOUT
        elif "network" in err_str or "connection" in err_str or "dns" in err_str:
            ftype = FailureType.NETWORK_FAILURE
        elif "unsupported format" in err_str or "unsupported file" in err_str:
            ftype = FailureType.UNSUPPORTED_FORMAT
            recoverable = False
        elif "corrupted" in err_str or "failed to open" in err_str:
            ftype = FailureType.DOCUMENT_CORRUPTED
            recoverable = False
        elif "extraction failed" in err_str or "could not extract" in err_str:
            ftype = FailureType.EXTRACTION_FAILED
        elif "insufficient" in err_str or "couldn't find enough information" in err_str:
            ftype = FailureType.INSUFFICIENT_CONTENT
            recoverable = False
        elif "web content unavailable" in err_str:
            ftype = FailureType.WEB_CONTENT_UNAVAILABLE
        elif "filesystem" in err_str or "file not found" in err_str or "directory" in err_str or "no such file" in err_str:
            ftype = FailureType.FILESYSTEM_ERROR
        elif "target not found" in err_str or "could not locate" in err_str or "element not found" in err_str:
            ftype = FailureType.TARGET_NOT_FOUND
        elif "target moved" in err_str:
            ftype = FailureType.TARGET_MOVED
        elif "not interactable" in err_str or "disabled" in err_str:
            ftype = FailureType.TARGET_NOT_INTERACTABLE
        elif "perception" in err_str or (observation and getattr(observation, "metadata", {}).get("observation_failed")):
            ftype = FailureType.PERCEPTION_UNAVAILABLE
            recoverable = False
        elif "dependency" in err_str or "prerequisite" in err_str:
            ftype = FailureType.DEPENDENCY_FAILED
        elif comparison_result and not getattr(comparison_result, "success", True):
            ftype = FailureType.EXPECTED_STATE_NOT_REACHED
            explanation = getattr(comparison_result, "explanation", "")
        elif verification_result and not getattr(verification_result, "verified", True):
            ftype = FailureType.VERIFICATION
            explanation = getattr(verification_result, "message", "")
        elif error:
            ftype = FailureType.ACTION_FAILED
        else:
            ftype = FailureType.UNKNOWN

        return FailureInfo(
            action=action,
            error=error,
            attempt=attempt,
            failure_type=ftype,
            task_id=task_id,
            environment=environment,
            explanation=explanation or f"Failure classified as {ftype}",
            recoverability=recoverable,
            metadata={"error_details": str(error or "")},
        )