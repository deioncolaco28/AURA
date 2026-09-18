"""
app/security/safety_manager.py

Safety, Risk, and Confidence Management for AURA.
Enforces grounded confidence scoring, multi-tier risk classification,
confirmation policies, critical path protection, and passive content isolation.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config.config import SafetyConfig, config
from app.config.constants import RiskLevel
from app.intelligence.action import Action, ActionType


@dataclass
class SafetyAssessment:
    """Result of a safety, risk, and confidence evaluation."""
    risk_level: str
    confidence: float
    is_safe: bool
    confirmation_required: bool
    reason: str = ""
    blocked_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class SafetyManager:
    """
    Central safety enforcement engine for AURA.
    Evaluates actions against safety policies, risk matrices,
    and evidence-grounded confidence scores.
    """

    CRITICAL_SYSTEM_PATHS = {
        "c:\\windows",
        "c:\\windows\\system32",
        "c:\\program files",
        "c:\\program files (x86)",
        "c:\\boot",
        "c:\\recovery",
        "/bin",
        "/sbin",
        "/usr",
        "/etc",
    }

    HIGH_RISK_ACTION_TYPES = {
        ActionType.DELETE_FILE,
        ActionType.DELETE_FOLDER,
        ActionType.TERMINATE_PROCESS,
    }

    MEDIUM_RISK_ACTION_TYPES = {
        ActionType.WRITE_FILE,
        ActionType.MOVE_FILE,
        ActionType.RENAME_FILE,
        ActionType.CLOSE_APPLICATION,
        ActionType.EXECUTE_COMMAND,
    }

    def __init__(self, safety_config: SafetyConfig | None = None):
        self.config = safety_config or config.safety

    def assess_action(
        self,
        action: Action,
        target_confidence: float = 1.0,
        is_ambiguous: bool = False,
        context_entities: dict[str, Any] | None = None,
    ) -> SafetyAssessment:
        """
        Assess risk, confidence, safety status, and confirmation need for an action.
        """
        # 1. Path sensitivity check
        target_path = str(action.target or "").strip()
        if self._is_critical_system_path(target_path):
            return SafetyAssessment(
                risk_level=RiskLevel.HIGH,
                confidence=target_confidence,
                is_safe=False,
                confirmation_required=True,
                reason="Target resides in a protected critical system path.",
                blocked_reason="BLOCKED_CRITICAL_SYSTEM_PATH",
            )

        # 2. Risk classification
        risk_level = self._classify_risk(action)

        # 3. Grounded confidence calculation
        confidence = self._calculate_confidence(
            action=action,
            base_confidence=target_confidence,
            is_ambiguous=is_ambiguous,
        )

        # 4. Confirmation policy check
        confirmation_required = self._should_require_confirmation(
            risk_level=risk_level,
            confidence=confidence,
            is_ambiguous=is_ambiguous,
        )

        # 5. Safety validity
        is_safe = True
        blocked_reason = None

        if not self.config.unrestricted_shell_allowed and action.action_type == ActionType.EXECUTE_COMMAND:
            # Prevent arbitrary destructive shell execution
            val = str(action.value or "").lower()
            if any(cmd in val for cmd in ["format", "del /f", "rm -rf", "shutdown"]):
                is_safe = False
                blocked_reason = "BLOCKED_DANGEROUS_SHELL_COMMAND"

        return SafetyAssessment(
            risk_level=risk_level,
            confidence=confidence,
            is_safe=is_safe,
            confirmation_required=confirmation_required,
            reason=f"Risk: {risk_level}, Confidence: {confidence:.2f}",
            blocked_reason=blocked_reason,
            metadata={"action_type": action.action_type, "target": target_path},
        )

    def _classify_risk(self, action: Action) -> str:
        """Determine risk level based on action type and target."""
        if action.action_type in self.HIGH_RISK_ACTION_TYPES:
            return RiskLevel.HIGH

        if action.action_type in self.MEDIUM_RISK_ACTION_TYPES:
            return RiskLevel.MEDIUM

        # Content creation is low risk (non-destructive overwrite handled gracefully)
        return RiskLevel.LOW

    def _calculate_confidence(
        self,
        action: Action,
        base_confidence: float,
        is_ambiguous: bool,
    ) -> float:
        """
        Calculate grounded confidence score based on concrete evidence.
        Penalizes ambiguity and missing target specifications.
        """
        score = max(0.0, min(1.0, base_confidence))

        if is_ambiguous:
            score *= 0.5

        if not action.target and action.action_type in (ActionType.CLICK, ActionType.TYPE_TEXT):
            score *= 0.3

        return round(score, 3)

    def _should_require_confirmation(
        self,
        risk_level: str,
        confidence: float,
        is_ambiguous: bool,
    ) -> bool:
        """Determine if user confirmation is required according to active policy."""
        policy = self.config.confirmation_policy

        if policy == "always":
            return True
        if policy == "never":
            return False

        # "high_risk_only" (default policy)
        if risk_level == RiskLevel.HIGH:
            return True

        if is_ambiguous or confidence < self.config.min_confidence_to_act:
            return True

        return False

    def _is_critical_system_path(self, path_str: str) -> bool:
        """Check if path targets critical operating system directories."""
        if not path_str:
            return False

        normalized = os.path.normpath(path_str).lower()
        for critical in self.CRITICAL_SYSTEM_PATHS:
            norm_crit = os.path.normpath(critical).lower()
            if normalized == norm_crit or normalized.startswith(norm_crit + os.sep):
                return True

        # Check drive roots (e.g., C:\)
        if normalized in ("c:\\", "c:", "/", "\\"):
            return True

        return False
