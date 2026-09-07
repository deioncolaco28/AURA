import time

from app.automation.action_executor import ActionExecutor
from app.automation.perception_executor import (
    PerceptionExecutor,
)
from app.config.constants import AssistantMode
from app.core.execution_engine import ExecutionEngine
from app.core.replanner import Replanner
from app.intelligence.action import ActionType
from app.intelligence.intent_parser import IntentParser
from app.intelligence.planner import Planner
from app.perception.ocr import TesseractOCR
from app.tutoring.tutor import Tutor
from app.tutoring.tutoring_controller import (
    TutoringController,
)
from app.verification.application_verifier import (
    ApplicationVerifier,
)
from app.verification.screen_verifier import (
    ScreenVerifier,
)
from app.voice.voice_manager import VoiceManager
from app.core.observer import ScreenObserver


class Agent:
    """
    Coordinates AURA perception, planning, execution,
    tutoring, verification, and recovery.
    """

    def __init__(
        self,
        voice_manager: VoiceManager,
        intent_parser: IntentParser | None = None,
        planner: Planner | None = None,
        action_executor: ActionExecutor | None = None,
        perception_executor: PerceptionExecutor | None = None,
        application_verifier: ApplicationVerifier | None = None,
        screen_verifier: ScreenVerifier | None = None,
        tutor: Tutor | None = None,
        tutoring_controller: TutoringController | None = None,
        execution_engine: ExecutionEngine | None = None,
        replanner: Replanner | None = None,
    ):
        self.voice_manager = voice_manager

        self.intent_parser = (
            intent_parser
            or IntentParser()
        )

        self.planner = (
            planner
            or Planner()
        )

        self.action_executor = (
            action_executor
            or ActionExecutor()
        )

        self.perception_executor = (
            perception_executor
            or PerceptionExecutor(
                action_executor=self.action_executor,
            )
        )

        self.application_verifier = (
            application_verifier
            or ApplicationVerifier()
        )

        self.screen_verifier = (
            screen_verifier
            or ScreenVerifier(
                ocr=TesseractOCR()
            )
        )

        self.tutor = (
            tutor
            or Tutor()
        )

        self.tutoring_controller = (
            tutoring_controller
            or TutoringController(
                voice_manager=voice_manager,
                ocr=TesseractOCR(),
            )
        )

        if execution_engine is not None:
            self.execution_engine = execution_engine

        else:
            self.execution_engine = (
                execution_engine
                or ExecutionEngine(
                    execute_action=self._execute_action,
                    verify_action=self._verify_action,
                    max_retries=1,
                    replanner=replanner,
                    max_replans=1,
                    observer=ScreenObserver(),
                )
            )

    def process_text(
        self,
        text: str,
    ) -> None:

        print(f"\nUser: {text}")

        intent = self.intent_parser.parse(
            text
        )

        print(
            f"Mode: {intent.mode}"
        )

        print(
            f"Goal: {intent.goal}"
        )

        print(
            f"Risk: {intent.risk_level}"
        )

        task = self.planner.create_task(
            intent
        )

        print(
            f"Planned actions: "
            f"{task.total_actions}"
        )

        if intent.mode == AssistantMode.SHOW_ME_HOW:
            self._run_tutoring_mode(
                task
            )
            return

        self._run_execution_mode(
            task
        )

    def _run_tutoring_mode(
        self,
        task,
    ) -> None:

        instructions = (
            self.tutor.create_instructions(
                task
            )
        )

        print(
            f"Tutorial instructions: "
            f"{len(instructions)}"
        )

        self.tutoring_controller.run(
            instructions
        )

        self.voice_manager.speak(
            "Tutoring session completed."
        )

    def _run_execution_mode(
        self,
        task,
    ) -> None:

        context = (
            self.execution_engine.run(
                task
            )
        )

        self._report_execution_result(
            context
        )

    def _execute_action(
        self,
        action,
    ):
        """
        Execute one action.

        UI actions use fresh screen perception.
        """

        print(
            f"Executing action: "
            f"{action.action_type}"
        )

        if action.action_type in (
            ActionType.CLICK,
            ActionType.DOUBLE_CLICK,
            ActionType.MOVE_MOUSE,
        ):
            return self.perception_executor.execute(
                action
            )

        self.action_executor.execute(
            action
        )

        action.execution_result = {
            "success": True,
        }

        return action

    def _verify_action(
        self,
        action,
    ) -> None:

        verification = action.verification

        if not verification:
            return

        verification_type = (
            verification.get("type")
        )

        if verification_type == "APPLICATION_RUNNING":
            self._verify_application_running(
                verification
            )
            return

        if verification_type == "SCREEN_CONTAINS_TEXT":
            self._verify_screen_contains_text(
                verification
            )
            return

        raise ValueError(
            f"Unsupported verification type: "
            f"{verification_type}"
        )

    def _verify_application_running(
        self,
        verification,
    ) -> None:

        process = verification.get(
            "process"
        )

        if not process:
            raise ValueError(
                "APPLICATION_RUNNING verification "
                "requires a process."
            )

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

            result = (
                self.application_verifier.verify(
                    process
                )
            )

            print(
                f"Verification attempt "
                f"{attempt}/{max_attempts}: "
                f"{result.message}"
            )

            if result.success:
                return

            if attempt < max_attempts:
                time.sleep(
                    retry_delay
                )

        raise RuntimeError(
            f"Application verification failed "
            f"after {max_attempts} attempts: "
            f"{result.message}"
        )

    def _verify_screen_contains_text(
        self,
        verification,
    ) -> None:

        text = verification.get(
            "text"
        )

        if not text:
            raise ValueError(
                "SCREEN_CONTAINS_TEXT verification "
                "requires text."
            )

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

            result = (
                self.screen_verifier.contains_text(
                    str(text)
                )
            )

            print(
                f"Screen verification attempt "
                f"{attempt}/{max_attempts}: "
                f"{result.message}"
            )

            if result.success:
                return

            if attempt < max_attempts:
                time.sleep(
                    retry_delay
                )

        raise RuntimeError(
            f"Screen verification failed "
            f"after {max_attempts} attempts: "
            f"{result.message}"
        )

    def _report_execution_result(
        self,
        context,
    ) -> None:

        if context.completed:
            print(
                "All execution steps completed."
            )

            self.voice_manager.speak(
                "Task completed."
            )

            return

        failed_steps = [
            step
            for step in context.steps
            if step.status == "FAILED"
        ]

        if failed_steps:
            failed = failed_steps[-1]

            print(
                f"Execution failed at step "
                f"{failed.index} "
                f"after {failed.attempts} attempts: "
                f"{failed.error}"
            )

            self.voice_manager.speak(
                "I could not complete that task."
            )

            return

        self.voice_manager.speak(
            "The task did not complete."
        )

    def run_once(self) -> None:

        text = (
            self.voice_manager.listen()
        )

        if not text:
            return

        self.process_text(
            text
        )