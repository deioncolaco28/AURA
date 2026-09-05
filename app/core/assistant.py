from app.config.constants import AssistantState
from app.core.state import AssistantState as RuntimeState


class Assistant:
    """Main controller for the AURA assistant."""

    def __init__(self):
        self.state = RuntimeState()

    def start(self):
        """Initialize the assistant."""

        self.state.current_state = AssistantState.IDLE

        print("Assistant initialized.")
        print(f"State: {self.state.current_state}")

    def stop(self):
        """Stop the assistant."""

        self.state.current_state = AssistantState.IDLE

        print("Assistant stopped.")

    def get_state(self) -> RuntimeState:
        """Return the current assistant state."""

        return self.state