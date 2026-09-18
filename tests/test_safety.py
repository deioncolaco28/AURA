"""
tests/test_safety.py

Unit tests for AURA Safety, Risk, and Confidence Management.
"""

from app.config.constants import RiskLevel
from app.intelligence.action import Action, ActionType
from app.security.safety_manager import SafetyManager


class TestSafetyManager:
    def setup_method(self):
        self.safety = SafetyManager()

    def test_low_risk_action_assessment(self):
        action = Action(action_type=ActionType.LAUNCH_APP, target="notepad.exe")
        assessment = self.safety.assess_action(action)

        assert assessment.risk_level == RiskLevel.LOW
        assert assessment.is_safe is True
        assert assessment.confirmation_required is False
        assert assessment.confidence == 1.0

    def test_high_risk_action_assessment(self):
        action = Action(action_type=ActionType.DELETE_FILE, target="C:\\Users\\test\\old.txt")
        assessment = self.safety.assess_action(action)

        assert assessment.risk_level == RiskLevel.HIGH
        assert assessment.is_safe is True
        assert assessment.confirmation_required is True

    def test_critical_system_path_blocking(self):
        action = Action(action_type=ActionType.DELETE_FILE, target="C:\\Windows\\System32\\calc.exe")
        assessment = self.safety.assess_action(action)

        assert assessment.risk_level == RiskLevel.HIGH
        assert assessment.is_safe is False
        assert assessment.confirmation_required is True
        assert assessment.blocked_reason == "BLOCKED_CRITICAL_SYSTEM_PATH"

    def test_dangerous_shell_command_blocking(self):
        action = Action(action_type=ActionType.EXECUTE_COMMAND, value="rm -rf /")
        assessment = self.safety.assess_action(action)

        assert assessment.is_safe is False
        assert assessment.blocked_reason == "BLOCKED_DANGEROUS_SHELL_COMMAND"

    def test_ambiguity_penalizes_confidence_and_requires_confirmation(self):
        action = Action(action_type=ActionType.CLICK, target="Button")
        assessment = self.safety.assess_action(action, target_confidence=0.8, is_ambiguous=True)

        assert assessment.confidence == 0.4
        assert assessment.confirmation_required is True

    def test_confirmation_policy_always(self):
        from app.config.config import SafetyConfig
        strict_safety = SafetyManager(safety_config=SafetyConfig(confirmation_policy="always"))

        action = Action(action_type=ActionType.LAUNCH_APP, target="notepad.exe")
        assessment = strict_safety.assess_action(action)
        assert assessment.confirmation_required is True

    def test_confirmation_policy_never(self):
        from app.config.config import SafetyConfig
        relaxed_safety = SafetyManager(safety_config=SafetyConfig(confirmation_policy="never"))

        action = Action(action_type=ActionType.DELETE_FILE, target="C:\\Users\\test\\file.txt")
        assessment = relaxed_safety.assess_action(action)
        assert assessment.confirmation_required is False
