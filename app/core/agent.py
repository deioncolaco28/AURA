from app.automation.action_executor import ActionExecutor
from app.intelligence.action import ActionType
from app.intelligence.intent_parser import IntentParser
from app.intelligence.planner import Planner
from app.voice.voice_manager import VoiceManager

class Agent:
    """Coordinates AURA's perception, planning, and execution."""

    def __init__(
        self,
        voice_manager: VoiceManager,
        intent_parser: IntentParser | None = None,
        planner: Planner | None = None,
        action_executor: ActionExecutor | None = None,
    ):
        self.voice_manager = voice_manager
        self.intent_parser = (
            intent_parser or IntentParser()
        )
        self.planner = planner or Planner()
        self.action_executor = (
            action_executor or ActionExecutor()
        )

    def process_text(self, text: str) -> None:
        """Process a single user request."""

        print(f"\nUser: {text}")

        intent = self.intent_parser.parse(text)

        print(f"Mode: {intent.mode}")
        print(f"Goal: {intent.goal}")
        print(f"Risk: {intent.risk_level}")

        task = self.planner.create_task(intent)

        print(
            f"Planned actions: {task.total_actions}"
        )

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

            self.action_executor.execute(action)

        self.voice_manager.speak(
            "Task completed."
        )

    def run_once(self) -> None:
        """Listen for and process one voice request."""

        text = self.voice_manager.listen()

        if not text:
            return

        self.process_text(text)