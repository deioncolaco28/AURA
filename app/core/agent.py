from app.config.constants import AssistantState
from app.core.execution_engine import ExecutionEngine
from app.core.state import AssistantState as RuntimeState
from app.intelligence.action import Action, ActionType
from app.intelligence.intent_parser import IntentParser
from app.intelligence.mode_router import ModeRouter
from app.intelligence.planner import Planner
from app.logging.logger import AURALogger


class Agent:
    """
    Main orchestration layer for AURA.

    Responsibilities:
        Voice/text input
            ↓
        Intent parsing
            ↓
        Mode routing
            ↓
        Task planning
            ↓
        Tutoring OR autonomous execution
            ↓
        Verification / recovery
    """

    DEFAULT_MAX_RETRIES = 5

    def __init__(
        self,
        intent_parser=None,
        mode_router=None,
        planner=None,
        execution_engine=None,
        voice_manager=None,
        action_executor=None,
        application_verifier=None,
        screen_verifier=None,
        logger=None,
        tutor=None,
        tutoring_controller=None,
    ):
        self.intent_parser = intent_parser or IntentParser()
        self.mode_router = mode_router or ModeRouter()
        self.planner = planner or Planner()
        self.voice_manager = voice_manager
        self.action_executor = action_executor
        self.application_verifier = application_verifier
        self.screen_verifier = screen_verifier
        self.logger = logger or AURALogger()
        self.tutor = tutor
        self.tutoring_controller = tutoring_controller
        self.interaction_history = None  # injected post-construction if needed

        if execution_engine is not None:
            self.execution_engine = execution_engine
        else:
            self.execution_engine = ExecutionEngine(
                execute_action=self._execute_action,
                verify_action=self._verify_action,
                max_retries=self.DEFAULT_MAX_RETRIES,
            )

        self.state = RuntimeState()

    # ------------------------------------------------------------------
    # MAIN ENTRY POINT
    # ------------------------------------------------------------------

    def process_text(self, text: str):
        """
        Process a user command from text/STT.

        Incomplete commands are rejected before planning so AURA
        does not create meaningless SPEAK actions.
        """

        if not text or not text.strip():
            raise ValueError("User input cannot be empty.")

        self.logger.command_received(text)

        print(f"\nUser command: {text}")

        # --------------------------------------------------------------
        # IMPORTANT:
        # Reject incomplete natural-language commands BEFORE planning.
        # This protects against IntentParser reducing:
        #
        #   "show me how to"
        #
        # into:
        #
        #   goal = "to"
        # --------------------------------------------------------------
        if self._is_incomplete_command(text):
            self.state.current_state = AssistantState.FAILED

            error = "Incomplete command."

            self.logger.task_failed(
                text.strip(),
                error,
            )

            print(
                "\nIncomplete command. "
                "Please specify what you would like me to do."
            )

            self._speak(
                "Please tell me what you would like me to do."
            )

            return None

        # --------------------------------------------------------------
        # UNDERSTANDING
        # --------------------------------------------------------------

        self.state.current_state = AssistantState.UNDERSTANDING

        intent = self.intent_parser.parse(text)

        print(f"Mode: {intent.mode}")
        print(f"Goal: {intent.goal}")
        print(f"Risk: {intent.risk_level}")

        self.logger.intent_detected(
            goal=intent.goal,
            mode=intent.mode,
            risk=intent.risk_level,
        )

        # --------------------------------------------------------------
        # CONFIRMATION
        # --------------------------------------------------------------

        if intent.requires_confirmation:
            print("Confirmation required for this task.")

            self._speak(
                "This task requires confirmation before I can continue."
            )

            self.state.current_state = AssistantState.IDLE

            return None

        # --------------------------------------------------------------
        # MODE + TASK
        # --------------------------------------------------------------

        self.state.current_mode = self.mode_router.route(intent)
        self.state.current_task = intent.goal

        self.state.current_state = AssistantState.PLANNING

        task = self.planner.create_task(intent)

        self.state.total_steps = task.total_actions

        print(
            f"Planned actions: {task.total_actions}"
        )

        for index, action in enumerate(
            task.actions,
            start=1,
        ):
            print(
                f"  {index}. {action.action_type}"
                + (
                    f" -> {action.target}"
                    if action.target
                    else ""
                )
            )

        if not task.actions:
            self.state.current_state = AssistantState.FAILED

            self.logger.task_failed(
                intent.goal,
                "No actions were generated.",
            )

            self._speak(
                "I could not create a plan for that task."
            )

            return None

        # --------------------------------------------------------------
        # EXECUTION / TUTORING
        # --------------------------------------------------------------

        if self.state.current_mode == "SHOW_ME_HOW":
            return self._run_tutoring_mode(
                task,
                intent.goal,
            )

        return self._run_execution_mode(
            task,
            intent.goal,
        )

    # ------------------------------------------------------------------
    # INCOMPLETE COMMAND DETECTION
    # ------------------------------------------------------------------

    @staticmethod
    def _is_incomplete_command(text: str) -> bool:
        """
        Detect commands that do not contain an actual task.

        This check intentionally operates on the RAW user input
        rather than the parsed intent because the IntentParser may
        normalize incomplete commands into misleading goals such as
        "to".
        """

        normalized = " ".join(
            text.strip().lower().split()
        )

        incomplete_commands = {
            "show me how",
            "show me how to",
            "do it for me",
            "do this for me",
            "open",
            "launch",
            "start",
            "go to",
        }

        return normalized in incomplete_commands

    # ------------------------------------------------------------------
    # AUTONOMOUS MODE
    # ------------------------------------------------------------------

    def _run_execution_mode(
        self,
        task,
        goal: str,
    ):
        self.state.current_state = AssistantState.ACTING

        context = self.execution_engine.run(task)

        if context.completed:
            self.state.current_state = AssistantState.COMPLETED

            self.logger.task_completed(goal)

            print(
                "\nTask completed successfully."
            )

            self._speak(
                "Task completed."
            )

        else:
            self.state.current_state = AssistantState.FAILED

            self.logger.task_failed(goal)

            print(
                "\nTask could not be completed."
            )

            self._speak(
                "I could not complete that task."
            )

        return context

    # ------------------------------------------------------------------
    # TUTORING MODE
    # ------------------------------------------------------------------

    def _run_tutoring_mode(
        self,
        task,
        goal: str,
    ):
        try:
            if self.tutor is None:
                from app.tutoring.tutor import Tutor

                self.tutor = Tutor()

            if self.tutoring_controller is None:
                from app.tutoring.tutoring_controller import (
                    TutoringController,
                )

                self.tutoring_controller = TutoringController(
                    voice_manager=self.voice_manager
                )

            self.state.current_state = AssistantState.ACTING

            instructions = self.tutor.create_instructions(
                task
            )

            if not instructions:
                self.state.current_state = AssistantState.FAILED

                error = (
                    "No tutoring instructions were generated."
                )

                self.logger.task_failed(
                    goal,
                    error,
                )

                self._speak(
                    "I could not create instructions for that task."
                )

                return None

            print(
                f"Generated tutoring instructions: "
                f"{len(instructions)}"
            )

            self.state.total_steps = len(
                instructions
            )

            self.tutoring_controller.run(
                instructions
            )

            completed = all(
                instruction.completed
                for instruction in instructions
            )

            if completed:
                self.state.current_state = AssistantState.COMPLETED

                self.logger.task_completed(goal)

                print(
                    "\nTutoring completed successfully."
                )

                self._speak(
                    "Tutoring completed."
                )

            else:
                self.state.current_state = AssistantState.FAILED

                self.logger.task_failed(
                    goal,
                    "One or more tutoring steps were not completed.",
                )

                print(
                    "\nTutoring could not be completed."
                )

                self._speak(
                    "I could not confirm all the tutoring steps."
                )

            return instructions

        except Exception as error:
            self.state.current_state = AssistantState.FAILED

            self.logger.task_failed(
                goal,
                str(error),
            )

            print(
                f"\nTutoring error: {error}"
            )

            self._speak(
                "I encountered an error while running tutoring mode."
            )

            return None

    # ------------------------------------------------------------------
    # ACTION EXECUTION
    # ------------------------------------------------------------------

    def _execute_action(
        self,
        action: Action,
    ) -> Action:

        if self.action_executor is not None:
            result = self.action_executor.execute(
                action
            )

            if isinstance(result, Action):
                return result

            return action

        from app.automation.action_executor import (
            ActionExecutor,
        )

        from app.automation.perception_executor import (
            PerceptionExecutor,
        )

        if action.action_type in (
            ActionType.CLICK,
            ActionType.DOUBLE_CLICK,
            ActionType.MOVE_MOUSE,
        ):
            executor = PerceptionExecutor()

        else:
            executor = ActionExecutor()

        result = executor.execute(
            action
        )

        if isinstance(result, Action):
            return result

        return action

    # ------------------------------------------------------------------
    # ACTION VERIFICATION
    # ------------------------------------------------------------------

    def _verify_action(
        self,
        action: Action,
    ) -> None:

        verification = getattr(
            action,
            "verification",
            {},
        )

        if not isinstance(
            verification,
            dict,
        ):
            verification = {}

        verification_type = verification.get(
            "type"
        )

        # --------------------------------------------------------------
        # APPLICATION RUNNING
        # --------------------------------------------------------------

        if verification_type == "APPLICATION_RUNNING":

            # IMPORTANT:
            # Preserve BOTH supported formats:
            #
            # {"process": "notepad.exe"}
            #
            # and:
            #
            # {"processes": ["CalculatorApp.exe", ...]}
            #
            # The previous implementation only extracted "process",
            # causing Calculator to fall back to action.target == "calc".
            processes = verification.get(
                "processes"
            )

            process = verification.get(
                "process"
            )

            if self.application_verifier is not None:

                if processes:
                    result = (
                        self.application_verifier.verify(
                            self._verification_action(
                                processes=processes
                            )
                        )
                    )

                elif process:
                    result = (
                        self.application_verifier.verify(
                            process
                        )
                    )

                else:
                    result = False

            else:
                from app.verification.application_verifier import (
                    ApplicationVerifier,
                )

                verifier = ApplicationVerifier()

                if processes:
                    result = verifier.verify(
                        self._verification_action(
                            processes=processes
                        )
                    )

                elif process:
                    result = verifier.verify(
                        process
                    )

                else:
                    result = False

            if not result:
                message = getattr(
                    result,
                    "message",
                    None,
                )

                raise RuntimeError(
                    message
                    or "Application verification failed."
                )

            return

        # --------------------------------------------------------------
        # SCREEN VERIFICATION
        # --------------------------------------------------------------

        if verification_type in (
            "SCREEN_CONTAINS_TEXT",
            "SCREEN_DOES_NOT_CONTAIN_TEXT",
            "SCREEN_CHANGED",
        ):

            if self.screen_verifier is not None:
                result = (
                    self.screen_verifier.verify(
                        action
                    )
                )

            else:
                from app.verification.screen_verifier import (
                    ScreenVerifier,
                )

                result = (
                    ScreenVerifier().verify(
                        action
                    )
                )

            if not result:
                message = getattr(
                    result,
                    "message",
                    None
                )

                raise RuntimeError(
                    message
                    or "Screen verification failed."
                )

            return

        # --------------------------------------------------------------
        # BROWSER URL VERIFICATION
        # --------------------------------------------------------------

        if verification_type == "BROWSER_URL":

            expected_url = str(
                verification.get(
                    "url",
                    ""
                )
            ).strip()

            actual_url = str(
                action.execution_result.get(
                    "url",
                    ""
                )
            ).strip()

            if not expected_url:
                raise RuntimeError(
                    "Browser verification requires a URL."
                )

            if not actual_url:
                raise RuntimeError(
                    "Browser action did not return a URL."
                )

            expected_normalized = (
                expected_url.rstrip("/")
            )

            actual_normalized = (
                actual_url.rstrip("/")
            )

            if (
                expected_normalized.lower()
                != actual_normalized.lower()
            ):
                raise RuntimeError(
                    "Browser verification failed: "
                    f"expected '{expected_url}', "
                    f"got '{actual_url}'."
                )

            return

        # Unknown/no verification:
        # intentionally do nothing.
        return

    # ------------------------------------------------------------------
    # VERIFICATION HELPER
    # ------------------------------------------------------------------

    @staticmethod
    def _verification_action(
        processes,
    ):
        """
        Create a minimal verification-compatible object.

        This allows ApplicationVerifier to receive the same
        {"processes": [...]} structure used by the task system
        without coupling Agent to a specific verifier implementation.
        """

        class VerificationAction:
            def __init__(
                self,
                process_list,
            ):
                self.verification = {
                    "processes": process_list
                }

        return VerificationAction(
            processes
        )

    # ------------------------------------------------------------------
    # VOICE
    # ------------------------------------------------------------------

    def _speak(
        self,
        message: str,
    ) -> None:

        if self.voice_manager is not None:
            self.voice_manager.speak(
                message
            )