"""
app/perception/errors.py

Structured error hierarchy for perception, UI grounding, and verification failures.
"""


class PerceptionError(Exception):
    """Base exception for all perception, grounding, and UI understanding errors."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class TargetNotFoundError(PerceptionError):
    """Raised when a specified target cannot be located on screen."""
    pass


class TargetAmbiguousError(PerceptionError):
    """Raised when multiple candidate UI elements match with similar plausibility."""

    def __init__(
        self,
        message: str,
        candidates: list | None = None,
        clarification_question: str = "",
        details: dict | None = None,
    ):
        super().__init__(message, details)
        self.candidates = candidates or []
        self.clarification_question = clarification_question


class TargetMovedError(PerceptionError):
    """Raised when an element has changed location significantly between observations."""
    pass


class TargetNotInteractableError(PerceptionError):
    """Raised when a detected element is disabled or cannot accept input."""
    pass


class ApplicationNotFoundError(PerceptionError):
    """Raised when a target application is not found running or visible."""
    pass


class ApplicationNotForegroundError(PerceptionError):
    """Raised when the expected application is not in the foreground."""
    pass


class ScrollLimitReachedError(PerceptionError):
    """Raised when the maximum scroll attempts are reached without locating the target."""
    pass


class PerceptionUnavailableError(PerceptionError):
    """Raised when no perception provider (Accessibility, OCR, VLM) is available."""
    pass


class LowConfidenceError(PerceptionError):
    """Raised when perception result confidence is below the acceptable threshold."""
    pass


class ExpectedStateNotReachedError(PerceptionError):
    """Raised when an action did not produce the expected state transition."""
    pass
