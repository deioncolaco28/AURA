"""
app/tutoring/tutor.py

Converts Task actions into human-readable TutoringInstruction objects
for SHOW_ME_HOW mode.

Design rules
------------
- Messages are semantic and based on action type, not application names.
- No application-specific hard-coding ("if target == 'Notepad'").
- create_instructions(task) signature is preserved for compatibility.
- The Tutor generates instructions; it never clicks, types, or presses keys.
- Overlay is not referenced here.
"""

from app.intelligence.action import ActionType
from app.intelligence.task import Task
from app.tutoring.instruction import TutoringInstruction


# ---------------------------------------------------------------------------
# Application process registry
# ---------------------------------------------------------------------------
# Used only for resolving a process name from an application name in
# LAUNCH_APPLICATION instructions.  Centralised here rather than scattered
# through the codebase.

_KNOWN_PROCESSES: dict[str, str] = {
    "notepad": "notepad.exe",
    "calc": "CalculatorApp.exe",
    "calculator": "CalculatorApp.exe",
    "mspaint": "mspaint.exe",
    "paint": "mspaint.exe",
    "explorer": "explorer.exe",
    "wordpad": "wordpad.exe",
}


def _resolve_process(application: str) -> str:
    """Return the process name for an application display name."""

    key = application.strip().lower()
    return _KNOWN_PROCESSES.get(key, f"{application}.exe")


# ---------------------------------------------------------------------------
# Tutor
# ---------------------------------------------------------------------------


class Tutor:
    """
    Creates conversational TutoringInstruction objects for SHOW_ME_HOW mode.

    Each Action in a Task is converted to one TutoringInstruction.
    Instructions are semantic:

        CLICK "Notepad"   → "Click Notepad."
        CLICK "Start"     → "Click Start."
        TYPE_TEXT "Hello" → "Type 'Hello' into the field."
        PRESS_KEY "win"   → "Press the Windows key."

    The Tutor does NOT:
        - perform any action
        - click, type, or press keys
        - depend on the overlay
        - hard-code application-specific logic beyond process-name resolution
    """

    def create_instructions(
        self,
        task: Task,
    ) -> list[TutoringInstruction]:
        """
        Convert task actions to tutoring instructions.

        Parameters
        ----------
        task : Task
            The planned task.  task.actions is iterated.

        Returns
        -------
        list[TutoringInstruction]
        """

        instructions: list[TutoringInstruction] = []

        for action in task.actions:
            instruction = self._action_to_instruction(action)

            if instruction is not None:
                instructions.append(instruction)

        return instructions

    # ------------------------------------------------------------------
    # Conversion logic
    # ------------------------------------------------------------------

    def _action_to_instruction(
        self,
        action,
    ) -> TutoringInstruction | None:

        # ----------------------------------------------------------
        # SPEAK — pure narration, no user action required
        # ----------------------------------------------------------
        if action.action_type == ActionType.SPEAK:
            return TutoringInstruction(
                message=str(action.value),
                action_type=ActionType.SPEAK,
            )

        # ----------------------------------------------------------
        # PRESS_KEY
        # ----------------------------------------------------------
        if action.action_type == ActionType.PRESS_KEY:
            return self._press_key_instruction(action)

        # ----------------------------------------------------------
        # TYPE_TEXT
        # ----------------------------------------------------------
        if action.action_type == ActionType.TYPE_TEXT:
            return self._type_text_instruction(action)

        # ----------------------------------------------------------
        # CLICK
        # ----------------------------------------------------------
        if action.action_type == ActionType.CLICK:
            return self._click_instruction(action)

        # ----------------------------------------------------------
        # LAUNCH_APPLICATION
        # ----------------------------------------------------------
        if action.action_type == ActionType.LAUNCH_APPLICATION:
            return self._launch_instruction(action)

        # ----------------------------------------------------------
        # WAIT
        # ----------------------------------------------------------
        if action.action_type == ActionType.WAIT:
            seconds = float(
                (action.parameters or {}).get("seconds", 1.0)
            )
            return TutoringInstruction(
                message=f"Please wait {seconds:.0f} second(s).",
                action_type=ActionType.WAIT,
                parameters={"seconds": seconds},
                completion={},
            )

        # Unknown action — skip
        return None

    # ------------------------------------------------------------------
    # Per-action builders
    # ------------------------------------------------------------------

    @staticmethod
    def _press_key_instruction(action) -> TutoringInstruction:
        key = str(action.value or "")
        key_lower = key.lower()

        if key_lower == "win":
            key_label = "the Windows key"
            expected_msg = "I'll wait for the Start menu to appear."
            success_msg = "Good. I can see that the screen changed."
            recovery_msg = (
                "I haven't detected the Windows menu yet. "
                "Please press the Windows key again."
            )
        elif key_lower == "enter":
            key_label = "Enter"
            expected_msg = "I'll wait for the expected result."
            success_msg = "Good. I can see that the screen changed."
            recovery_msg = (
                "I haven't detected the expected change yet. "
                "Please press Enter again."
            )
        elif key_lower in ("ctrl+c", "ctrl+v", "ctrl+s", "ctrl+z"):
            key_label = key.upper()
            expected_msg = "I'll wait for you."
            success_msg = f"Good. {key_label} was applied."
            recovery_msg = (
                f"I haven't detected the expected change yet. "
                f"Please press {key_label} again."
            )
        else:
            key_label = key
            expected_msg = "I'll wait for you."
            success_msg = f"Good. The {key_label} key was applied."
            recovery_msg = (
                f"I haven't detected the expected change yet. "
                f"Please press the {key_label} key again."
            )

        return TutoringInstruction(
            message=(
                f"Press {key_label}. "
                f"{expected_msg}"
            ),
            action_type=ActionType.PRESS_KEY,
            parameters={"key": key},
            completion={"screen_changed": True},
            expected_transition={"screen_changed": True},
            success_message=success_msg,
            recovery={
                "message": recovery_msg,
                "max_attempts": 2,
            },
        )

    @staticmethod
    def _type_text_instruction(action) -> TutoringInstruction:
        text = str(action.value or "")

        return TutoringInstruction(
            message=(
                f"Type '{text}' into the search field."
            ),
            action_type=ActionType.TYPE_TEXT,
            parameters={"text": text},
            completion={"screen_contains": text},
            expected_transition={
                "text_appears": text,
                "requires_baseline": True,
            },
            success_message=(
                f"I can see '{text}' on the screen."
            ),
            recovery={
                "message": (
                    f"I can't see '{text}' yet. "
                    "Please type it into the search field."
                ),
                "max_attempts": 2,
            },
        )

    @staticmethod
    def _click_instruction(action) -> TutoringInstruction:
        target = action.target or "the element"

        # Determine completion condition.
        # Prefer an explicit verification from the planner; otherwise
        # use a generic expected-transition rather than just "target disappears".
        if action.verification:
            completion = dict(action.verification)
            expected_transition = dict(action.verification)
        else:
            completion = {"target_disappears": target}
            expected_transition = {
                "target_disappears": target,
                "or_process_starts": True,
            }

        # Determine success message.
        success_message = f"Done. {target} was activated."

        # Build the instruction message — semantic, not overlay-based.
        message = f"Click {target}."

        return TutoringInstruction(
            message=message,
            target=target,
            action_type=ActionType.CLICK,
            completion=completion,
            expected_transition=expected_transition,
            success_message=success_message,
            recovery={
                "message": (
                    f"I haven't detected the click result yet. "
                    f"Please click {target}."
                ),
                "max_attempts": 2,
            },
        )

    @staticmethod
    def _launch_instruction(action) -> TutoringInstruction:
        application = action.target or "the application"
        process = _resolve_process(application)

        return TutoringInstruction(
            message=(
                f"Open {application}. "
                "I'll confirm when it is running."
            ),
            target=application,
            action_type=ActionType.LAUNCH_APPLICATION,
            completion={
                "application_running": f"{application}.exe"
            },
            expected_transition={
                "process_starts": process,
            },
            success_message=(
                f"Perfect. {application} is now open."
            ),
            recovery={
                "message": (
                    f"I can't detect {application} yet. "
                    f"Please open {application} and I'll check again."
                ),
                "max_attempts": 2,
            },
        )