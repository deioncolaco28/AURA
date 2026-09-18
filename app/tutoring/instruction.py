"""
app/tutoring/instruction.py

Extended TutoringInstruction data model.

All original fields are preserved for backwards compatibility.
New fields support the new state-machine-based tutoring controller
and observation-diff verification.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TutoringInstruction:
    """
    Represents one interactive tutoring step.

    Original fields (preserved)
    ---------------------------
    message : str
        The instruction to speak to the user.
    target : str | None
        Text label of the UI target element.
    action_type : str | None
        The action the user should perform (ActionType constant).
    parameters : dict
        Action-specific parameters (e.g. {"text": "Notepad"}).
    completion : dict
        Completion condition (kept for backwards-compatibility).
    recovery : dict
        Recovery strategy when user does not complete the step.
    success_message : str | None
        Spoken message when the step is verified as complete.
    waiting_message : str | None
        Spoken message while waiting for user action.
    completed : bool
        True when this step has been verified as complete.
    attempts : int
        Number of times the instruction has been (re-)spoken.

    New fields (Phase 4 refactor)
    ------------------------------
    target_query : Any | None
        Structured TargetQuery for this step (used by TutoringEngine
        and SpatialReasoner to locate and describe the target).
    baseline_observation : Any | None
        ScreenObservation captured immediately BEFORE the user is
        asked to act.  Essential for before/after comparison and
        prevents false-positive completion detection.
    expected_transition : dict
        Description of what MUST change in the screen observation
        for this step to be considered complete.  More expressive
        than the legacy 'completion' dict.
        Examples:
            {"process_starts": "notepad.exe"}
            {"text_appears": "Notepad"}
            {"text_changes_in_field": "Hello World"}
            {"screen_region_changes": True}
    """

    message: str

    # ------------------------------------------------------------------
    # Original fields — preserved exactly
    # ------------------------------------------------------------------

    target: str | None = None

    action_type: str | None = None

    parameters: dict[str, Any] = field(
        default_factory=dict
    )

    completion: dict[str, Any] = field(
        default_factory=dict
    )

    recovery: dict[str, Any] = field(
        default_factory=dict
    )

    success_message: str | None = None

    waiting_message: str | None = None

    completed: bool = False

    attempts: int = 0

    # ------------------------------------------------------------------
    # New fields (Phase 4)
    # ------------------------------------------------------------------

    #: Structured TargetQuery — used by TutoringEngine for spatial resolution.
    target_query: Any | None = None

    #: Baseline ScreenObservation captured before user acts.
    #: Used for before/after comparison; prevents false-positive completion.
    baseline_observation: Any | None = None

    #: Expected state transition — what must change for step to be complete.
    expected_transition: dict[str, Any] = field(
        default_factory=dict
    )