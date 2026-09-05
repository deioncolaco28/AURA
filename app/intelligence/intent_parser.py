from app.config.constants import AssistantMode, RiskLevel
from app.intelligence.intent import Intent


class IntentParser:
    """Converts user text into a structured intent."""

    SHOW_ME_HOW_PHRASES = (
        "show me how",
        "teach me",
        "guide me",
        "how do i",
        "how can i",
    )

    HIGH_RISK_PHRASES = (
        "delete",
        "remove",
        "format",
        "send money",
        "transfer money",
        "purchase",
        "buy",
    )

    def parse(self, text: str) -> Intent:
        """Parse raw user text into an Intent."""

        normalized = text.strip().lower()

        if not normalized:
            raise ValueError("User input cannot be empty.")

        mode = self._detect_mode(normalized)
        risk_level = self._detect_risk(normalized)

        requires_confirmation = risk_level != RiskLevel.LOW

        goal = self._extract_goal(
            text=text.strip(),
            mode=mode,
        )

        return Intent(
            raw_text=text.strip(),
            goal=goal,
            mode=mode,
            risk_level=risk_level,
            requires_confirmation=requires_confirmation,
        )

    def _detect_mode(self, text: str) -> str:
        """Determine which assistant mode the user wants."""

        for phrase in self.SHOW_ME_HOW_PHRASES:
            if phrase in text:
                return AssistantMode.SHOW_ME_HOW

        return AssistantMode.DO_IT_FOR_ME

    def _detect_risk(self, text: str) -> str:
        """Determine the initial risk level."""

        for phrase in self.HIGH_RISK_PHRASES:
            if phrase in text:
                return RiskLevel.HIGH

        return RiskLevel.LOW

    def _extract_goal(
        self,
        text: str,
        mode: str,
    ) -> str:
        """Extract the user's underlying goal."""

        goal = text

        if mode == AssistantMode.SHOW_ME_HOW:
            prefixes = (
                "show me how to ",
                "show me how ",
                "teach me to ",
                "teach me how to ",
                "guide me to ",
                "how do i ",
                "how can i ",
            )

            normalized = text.lower()

            for prefix in prefixes:
                if normalized.startswith(prefix):
                    return text[len(prefix):].strip()

        return goal