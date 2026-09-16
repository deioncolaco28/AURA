from app.intelligence.action import ActionType
from app.intelligence.task import Task
from app.tutoring.instruction import TutoringInstruction


class Tutor:
    """
    Creates conversational instructions for
    Show Me How mode.
    """

    def create_instructions(
        self,
        task: Task,
    ) -> list[TutoringInstruction]:
        """
        Convert a task into interactive tutoring
        instructions.
        """

        instructions = []

        for action in task.actions:
            instruction = (
                self._action_to_instruction(
                    action
                )
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
        """
        Convert one planned action into a
        conversational tutoring instruction.
        """

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
                        "I'll wait for the Start menu "
                        "to appear."
                    ),
                    action_type=ActionType.PRESS_KEY,
                    parameters={
                        "key": key,
                    },
                    completion={
                        "screen_changed": True,
                    },
                    success_message=(
                        "Good. I can see that the "
                        "screen changed."
                    ),
                    recovery={
                        "message": (
                            "I haven't detected the "
                            "Windows menu yet. "
                            "Please press the Windows "
                            "key again."
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
                    "key": key,
                },
                completion={
                    "screen_changed": True,
                },
                success_message=(
                    f"Good. The {key} key was detected."
                ),
                recovery={
                    "message": (
                        f"I haven't detected the "
                        f"expected change yet. "
                        f"Please press the {key} "
                        f"key again."
                    ),
                    "max_attempts": 2,
                },
            )

        if action.action_type == ActionType.TYPE_TEXT:
            text = str(action.value)

            return TutoringInstruction(
                message=(
                    f"Great. Now type "
                    f"'{text}' into the search box. "
                    "I'll let you know when I can "
                    "see it."
                ),
                action_type=ActionType.TYPE_TEXT,
                parameters={
                    "text": text,
                },
                completion={
                    "screen_contains": text,
                },
                success_message=(
                    f"Perfect. I can see "
                    f"'{text}' on the screen."
                ),
                recovery={
                    "message": (
                        f"I can't see '{text}' yet. "
                        f"Please type it into the "
                        f"search field."
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
                    f"Excellent. I found "
                    f"{target} and highlighted it. "
                    f"Now click it to continue."
                ),
                target=target,
                action_type=ActionType.CLICK,
                completion=completion,
                success_message=(
                    f"Perfect. {target} has been opened."
                ),
                recovery={
                    "message": (
                        f"I haven't detected the "
                        f"click yet. Please click "
                        f"the highlighted {target}."
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
                    "I'll wait and confirm when "
                    "it is running."
                ),
                target=application,
                action_type=ActionType.LAUNCH_APPLICATION,
                completion={
                    "application_running": (
                        f"{application}.exe"
                    ),
                },
                success_message=(
                    f"Perfect. {application} is now open."
                ),
                recovery={
                    "message": (
                        f"I can't detect {application} "
                        "yet. Please open it and I'll "
                        "check again."
                    ),
                    "max_attempts": 2,
                },
            )

        return None