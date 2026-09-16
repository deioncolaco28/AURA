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
    Main coordinator for AURA.

    Pipeline:

        Text
          ↓
        Intent
          ↓
        Mode
          ↓
        Planner
          ↓
        Task
          ↓
        Execution Engine
          ↓
        Execute
          ↓
        Verify
          ↓
        Recover / Replan
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
    ):
        self.intent_parser = intent_parser or IntentParser()
        self.mode_router = mode_router or ModeRouter()
        self.planner = planner or Planner()
        self.voice_manager = voice_manager
        self.action_executor = action_executor
        self.application_verifier = application_verifier
        self.screen_verifier = screen_verifier
        self.logger = logger or AURALogger()

        if execution_engine is not None:
            self.execution_engine = execution_engine
        else:
            self.execution_engine = ExecutionEngine(
                execute_action=self._execute_action,
                verify_action=self._verify_action,
                max_retries=self.DEFAULT_MAX_RETRIES,
            )

        self.state = RuntimeState()

    def process_text(self, text: str):
        if not text or not text.strip():
            raise ValueError("User input cannot be empty.")

        self.logger.command_received(text)

        print(f"\nUser command: {text}")

        self.state.current_state = (
            AssistantState.UNDERSTANDING
        )

        intent = self.intent_parser.parse(text)

        print(f"Mode: {intent.mode}")
        print(f"Goal: {intent.goal}")
        print(f"Risk: {intent.risk_level}")

        self.logger.intent_detected(
            goal=intent.goal,
            mode=intent.mode,
            risk=intent.risk_level,
        )

        if intent.requires_confirmation:
            print(
                "Confirmation required for this task."
            )

            self.state.current_state = (
                AssistantState.IDLE
            )

            return None

        self.state.current_mode = (
            self.mode_router.route(intent)
        )

        self.state.current_task = intent.goal

        self.state.current_state = (
            AssistantState.PLANNING
        )

        task = self.planner.create_task(intent)

        self.state.total_steps = (
            task.total_actions
        )

        print(
            f"Planned actions: "
            f"{task.total_actions}"
        )

        for index, action in enumerate(
            task.actions,
            start=1,
        ):
            print(
                f"  {index}. "
                f"{action.action_type}"
                + (
                    f" -> {action.target}"
                    if action.target
                    else ""
                )
            )

        if not task.actions:
            self.state.current_state = (
                AssistantState.FAILED
            )
            return None

        self.state.current_state = (
            AssistantState.ACTING
        )

        context = self.execution_engine.run(
            task
        )

        if context.completed:
            self.state.current_state = (
                AssistantState.COMPLETED
            )

            self.logger.task_completed(
                intent.goal
            )

            print(
                "\nTask completed successfully."
            )

            self._speak(
                "Task completed."
            )

        else:
            self.state.current_state = (
                AssistantState.FAILED
            )

            self.logger.task_failed(
                intent.goal
            )

            print(
                "\nTask could not be completed."
            )

            self._speak(
                "I could not complete that task."
            )

        return context

    def _execute_action(
        self,
        action: Action,
    ) -> Action:

        if self.action_executor is not None:
            result = (
                self.action_executor.execute(
                    action
                )
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

        result = executor.execute(action)

        if isinstance(result, Action):
            return result

        return action

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

        verification_type = (
            verification.get("type")
        )

        if (
            verification_type
            == "APPLICATION_RUNNING"
        ):
            process = (
                verification.get("process")
                or getattr(
                    action,
                    "target",
                    None,
                )
            )

            if self.application_verifier is not None:
                result = (
                    self.application_verifier.verify(
                        process
                    )
                )
            else:
                from app.verification.application_verifier import (
                    ApplicationVerifier,
                )

                result = (
                    ApplicationVerifier().verify(
                        process
                    )
                )

            if not result:
                raise RuntimeError(
                    getattr(
                        result,
                        "message",
                        "Application verification failed.",
                    )
                )

            return

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
                raise RuntimeError(
                    getattr(
                        result,
                        "message",
                        "Screen verification failed.",
                    )
                )

            return

        return

    def _speak(
        self,
        message: str,
    ) -> None:

        if self.voice_manager is not None:
            self.voice_manager.speak(
                message
            )