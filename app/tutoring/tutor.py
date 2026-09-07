from app.intelligence.action import ActionType
from app.intelligence.task import Task
from app.tutoring.instruction import TutoringInstruction


class Tutor:
    """Creates instructions for Show Me How mode."""

    def create_instructions(
        self,
        task: Task,
    ) -> list[TutoringInstruction]:
        """Convert a task into tutoring instructions."""

        instructions = []

        for action in task.actions:
            instruction = self._action_to_instruction(
                action
            )

            if instruction is not None:
                instructions.append(
                    instruction
                )

        return instructions

    def _action_to_instruction(
        self,
        action,
    ) -> TutoringInstruction | None:
        """Convert an action into a tutoring instruction."""

        if action.action_type == ActionType.SPEAK:
            return TutoringInstruction(
                message=str(action.value),
                action_type=ActionType.SPEAK,
            )

        if action.action_type == ActionType.PRESS_KEY:
            key = str(action.value)

            if key.lower() == "win":
                return TutoringInstruction(
                    message=(
                        "Press the Windows key."
                    ),
                    action_type=ActionType.PRESS_KEY,
                    parameters={
                        "key": key,
                    },
                    completion={
                        "screen_changed": True,
                    },
                    recovery={
                        "message": (
                            "Please press the "
                            "Windows key again."
                        ),
                        "max_attempts": 2,
                    },
                )

            return TutoringInstruction(
                message=f"Press the {key} key.",
                action_type=ActionType.PRESS_KEY,
                parameters={
                    "key": key,
                },
                completion={
                    "screen_changed": True,
                },
                recovery={
                    "message": (
                        f"Please press the {key} "
                        "key again."
                    ),
                    "max_attempts": 2,
                },
            )

        if action.action_type == ActionType.TYPE_TEXT:
            text = str(action.value)

            return TutoringInstruction(
                message=f"Type {text}.",
                action_type=ActionType.TYPE_TEXT,
                parameters={
                    "text": text,
                },
                completion={
                    "screen_contains": text,
                },
                recovery={
                    "message": (
                        f"Please type {text} "
                        "into the search field."
                    ),
                    "max_attempts": 2,
                },
            )

        if action.action_type == ActionType.CLICK:
            target = (
                action.target
                or "the requested element"
            )

            completion = action.verification.copy()

            if not completion:
                completion = {
                    "target_disappears": target
                }

            return TutoringInstruction(
                message=(
                    f"Click the highlighted "
                    f"{target}."
                ),
                target=target,
                action_type=ActionType.CLICK,
                completion=completion,
                recovery={
                    "message": (
                        f"Please click the "
                        f"highlighted {target}."
                    ),
                    "max_attempts": 2,
                },
            )

        if action.action_type == ActionType.LAUNCH_APPLICATION:
            application = (
                action.target
                or "the application"
            )

            return TutoringInstruction(
                message=f"Open {application}.",
                target=application,
                action_type=ActionType.LAUNCH_APPLICATION,
                completion={
                    "application_running": (
                        f"{application}.exe"
                    ),
                },
                recovery={
                    "message": (
                        f"Please open "
                        f"{application}."
                    ),
                    "max_attempts": 2,
                },
            )

        return None