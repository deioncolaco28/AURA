from app.config.constants import AssistantMode
from app.intelligence.intent import Intent


class ModeRouter:
    """Determines which AURA mode should handle an intent."""

    def route(self, intent: Intent) -> str:
        """Return the mode selected for the intent."""

        return intent.mode