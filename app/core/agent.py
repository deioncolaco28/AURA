import time

from app.automation.action_executor import ActionExecutor
from app.intelligence.action import ActionType
from app.intelligence.intent_parser import IntentParser
from app.intelligence.planner import Planner
from app.perception.ocr import TesseractOCR
from app.tutoring.tutor import Tutor
from app.tutoring.tutoring_controller import TutoringController
from app.verification.application_verifier import ApplicationVerifier
from app.voice.voice_manager import VoiceManager


class Agent:
    """Coordinates AURA perception, planning, execution,
    tutoring, and verification.
    """

    def __init__(
        self,
        voice_manager: VoiceManager,
        intent_parser: IntentParser | None = None,
        planner: Planner | None = None,
        action_executor: ActionExecutor | None = None,
        application_verifier: ApplicationVerifier | None = None,
        tutor: Tutor | None = None,
        tutoring_controller: TutoringController | None = None,
    ):
        self.voice_manager = voice_manager
        self.intent_parser = intent_parser or IntentParser()
        self.planner = planner or Planner()
        self.action_executor = action_executor or ActionExecutor()
        self.application_verifier = (
            application_verifier or ApplicationVerifier()
        )
        self.tutor = tutor or Tutor()
        self.tutoring_controller = (
            tutoring_controller
            or TutoringController(
                voice_manager=voice_manager,
                ocr=TesseractOCR(),
            )
        )

    def process_text(self, text: str) -> None:
        """Process one text command."""

        print(f"\nUser: {text}")

        intent = self.intent_parser.parse(text)

        print(f"Mode: {intent.mode}")
        print(f"Goal: {intent.goal}")
        print(f"Risk: {intent.risk_level}")

        task = self.planner.create_task(intent)

        print(f"Planned actions: {task.total_actions}")

        if intent.mode == "SHOW_ME_HOW":
            self._run_tutoring_mode(task)
            return

        self._run_execution_mode(task)

    def _run_tutoring_mode(self, task) -> None:
        """Run the Show Me How tutoring workflow."""

        instructions = self.tutor.create_instructions(task)

        print(
            f"Tutorial instructions: "
            f"{len(instructions)}"
        )

        self.tutoring_controller.run(instructions)

        self.voice_manager.speak(
            "Tutoring session completed."
        )

    def _run_execution_mode(self, task) -> None:
        """Execute a Do It For Me task."""

        for index, action in enumerate(
            task.actions,
            start=1,
        ):
            print(
                f"Executing action "
                f"{index}/{task.total_actions}: "
                f"{action.action_type}"
            )

            if action.action_type == ActionType.SPEAK:
                self.voice_manager.speak(
                    str(action.value)
                )
                continue

            try:
                self.action_executor.execute(action)
                self._verify_action(action)

            except Exception as error:
                print(f"Action failed: {error}")

                self.voice_manager.speak(
                    "I could not complete that action."
                )

                return

        self.voice_manager.speak(
            "Task completed."
        )

    def _verify_action(self, action) -> None:
        """Verify an action when verification is configured."""

        verification = action.verification

        if not verification:
            return

        verification_type = verification.get("type")

        if verification_type == "APPLICATION_RUNNING":
            process = verification.get("process")

            max_attempts = verification.get(
                "max_attempts",
                3,
            )

            retry_delay = verification.get(
                "retry_delay",
                0.5,
            )

            for attempt in range(
                1,
                max_attempts + 1,
            ):
                result = self.application_verifier.verify(
                    process
                )

                print(
                    f"Verification attempt "
                    f"{attempt}/{max_attempts}: "
                    f"{result.message}"
                )

                if result.success:
                    return

                if attempt < max_attempts:
                    time.sleep(retry_delay)

            raise RuntimeError(
                f"Action verification failed after "
                f"{max_attempts} attempts: "
                f"{result.message}"
            )

    def run_once(self) -> None:
        """Listen for and process one voice command."""

        text = self.voice_manager.listen()

        if not text:
            return

        self.process_text(text)