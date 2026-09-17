from app.intelligence.action import ActionType
from app.intelligence.task import Task
from app.tutoring.instruction import TutoringInstruction


class Tutor:
    """
    Creates conversational instructions for SHOW_ME_HOW mode.
    """

    def create_instructions(
        self,
        task: Task,
    ) -> list[TutoringInstruction]:
        instructions = []

        for action in task.actions:
            instruction = self._action_to_instruction(action)

            if instruction is not None:
                instructions.append(instruction)

        return instructions

    def _action_to_instruction(
        self,
        action,
    ) -> TutoringInstruction | None:

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
                        "First, press the Windows key. "
                        "I'll wait for the Start menu to appear."
                    ),
                    action_type=ActionType.PRESS_KEY,
                    parameters={
                        "key": key
                    },
                    completion={
                        "screen_changed": True
                    },
                    success_message=(
                        "Good. I can see that the screen changed."
                    ),
                    recovery={
                        "message": (
                            "I haven't detected the Windows menu yet. "
                            "Please press the Windows key again."
                        ),
                        "max_attempts": 2,
                    },
                )

            return TutoringInstruction(
                message=(
                    f"Please press the {key} key. "
                    "I'll wait for you."
                ),
                action_type=ActionType.PRESS_KEY,
                parameters={
                    "key": key
                },
                completion={
                    "screen_changed": True
                },
                success_message=(
                    f"Good. The {key} key was detected."
                ),
                recovery={
                    "message": (
                        "I haven't detected the expected change yet. "
                        f"Please press the {key} key again."
                    ),
                    "max_attempts": 2,
                },
            )

        if action.action_type == ActionType.TYPE_TEXT:
            text = str(action.value)

            return TutoringInstruction(
                message=(
                    f"Great. Now type '{text}' into the search box. "
                    "I'll let you know when I can see it."
                ),
                action_type=ActionType.TYPE_TEXT,
                parameters={
                    "text": text
                },
                completion={
                    "screen_contains": text
                },
                success_message=(
                    f"Perfect. I can see '{text}' on the screen."
                ),
                recovery={
                    "message": (
                        f"I can't see '{text}' yet. "
                        "Please type it into the search field."
                    ),
                    "max_attempts": 2,
                },
            )

        if action.action_type == ActionType.CLICK:
            target = (
                action.target
                or "the requested element"
            )

            if target.lower() == "notepad":
                completion = {
                    "type": "APPLICATION_RUNNING",
                    "process": "notepad.exe",
                }

                success_message = (
                    "Perfect. Notepad has been opened."
                )

            else:
                completion = (
                    action.verification.copy()
                    if action.verification
                    else {
                        "target_disappears": target
                    }
                )

                success_message = (
                    f"Perfect. {target} has been opened."
                )

            return TutoringInstruction(
                message=(
                    f"Excellent. I found {target} "
                    "and highlighted it. "
                    "Now click it to continue."
                ),
                target=target,
                action_type=ActionType.CLICK,
                completion=completion,
                success_message=success_message,
                recovery={
                    "message": (
                        f"I haven't detected the click yet. "
                        f"Please click the highlighted {target}."
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
                message=(
                    f"Please open {application}. "
                    "I'll wait and confirm when it is running."
                ),
                target=application,
                action_type=ActionType.LAUNCH_APPLICATION,
                completion={
                    "application_running":
                        f"{application}.exe"
                },
                success_message=(
                    f"Perfect. {application} is now open."
                ),
                recovery={
                    "message": (
                        f"I can't detect {application} yet. "
                        "Please open it and I'll check again."
                    ),
                    "max_attempts": 2,
                },
            )

        return None