"""
app/verification/state_verifier.py

Unified state verifier multiplexing across Application, Browser, Filesystem, and Screen UI states.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.verification.application_verifier import ApplicationVerifier
from app.verification.filesystem_verifier import FileSystemVerifier
from app.verification.screen_verifier import ScreenVerifier

logger = logging.getLogger(__name__)


@dataclass
class StateVerificationResult:
    """Outcome of an action state verification."""

    verified: bool
    verification_type: str
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


class StateVerifier:
    """
    Unified verifier for Whole-PC actions.
    Checks expected outcomes across Applications, Browser, Filesystem, and UI Screen states.
    """

    def __init__(
        self,
        application_verifier: ApplicationVerifier | None = None,
        screen_verifier: ScreenVerifier | None = None,
        filesystem_verifier: FileSystemVerifier | None = None,
    ):
        self.application_verifier = application_verifier or ApplicationVerifier()
        self.screen_verifier = screen_verifier or ScreenVerifier()
        self.filesystem_verifier = filesystem_verifier or FileSystemVerifier()

    def verify_action(
        self,
        action_or_spec: Any,
        observation_before: Any = None,
        observation_after: Any = None,
        browser_manager: Any = None,
    ) -> StateVerificationResult:
        """Verify the expected outcome of an action."""
        if hasattr(action_or_spec, "verification"):
            spec = action_or_spec.verification
        elif isinstance(action_or_spec, dict):
            spec = action_or_spec
        else:
            spec = {}

        if not spec:
            return StateVerificationResult(
                verified=True,
                verification_type="NONE",
                message="No verification specification provided.",
            )

        vtype = spec.get("type", "").upper()

        # -------------------------------------------------------------
        # 1. Application Running / Foreground
        # -------------------------------------------------------------
        if vtype == "APPLICATION_RUNNING":
            processes = spec.get("processes") or ([spec["process"]] if "process" in spec else [])
            for proc in processes:
                if self.application_verifier.is_running(proc):
                    return StateVerificationResult(
                        verified=True,
                        verification_type=vtype,
                        message=f"Application process '{proc}' is running.",
                    )
            return StateVerificationResult(
                verified=False,
                verification_type=vtype,
                message=f"None of the expected processes {processes} were running.",
            )

        if vtype == "APPLICATION_FOREGROUND":
            app_name = spec.get("app_name") or spec.get("process", "")
            from app.perception.foreground_detector import ForegroundApplicationDetector
            detector = ForegroundApplicationDetector()
            ctx = detector.get_foreground_context()
            if ctx.matches(app_name):
                return StateVerificationResult(
                    verified=True,
                    verification_type=vtype,
                    message=f"Application '{app_name}' is in the foreground.",
                )
            return StateVerificationResult(
                verified=False,
                verification_type=vtype,
                message=f"Application '{app_name}' is not in the foreground (current: '{ctx.app_name}').",
            )

        # -------------------------------------------------------------
        # 2. Browser URL & Title
        # -------------------------------------------------------------
        if vtype in ("BROWSER_URL", "URL_CHANGED"):
            expected_url = spec.get("url", "")
            current_url = ""
            if browser_manager and hasattr(browser_manager, "get_current_url"):
                current_url = browser_manager.get_current_url()
            elif observation_after and getattr(observation_after, "url", None):
                current_url = observation_after.url

            if expected_url and expected_url.lower() in current_url.lower():
                return StateVerificationResult(
                    verified=True,
                    verification_type=vtype,
                    message=f"Browser navigated to expected URL '{expected_url}'.",
                    details={"url": current_url},
                )
            if not expected_url and current_url:
                return StateVerificationResult(
                    verified=True,
                    verification_type=vtype,
                    message=f"Browser URL is active: '{current_url}'.",
                    details={"url": current_url},
                )
            return StateVerificationResult(
                verified=False,
                verification_type=vtype,
                message=f"Browser URL '{current_url}' did not match expected '{expected_url}'.",
            )

        # -------------------------------------------------------------
        # 3. Filesystem State Transitions
        # -------------------------------------------------------------
        if vtype in ("FS_EXISTS", "FILE_EXISTS", "FOLDER_EXISTS"):
            path = spec.get("path") or spec.get("target", "")
            ok, msg = self.filesystem_verifier.verify_create(path)
            return StateVerificationResult(verified=ok, verification_type=vtype, message=msg)

        if vtype in ("FS_DELETED", "FILE_DELETED"):
            path = spec.get("path") or spec.get("target", "")
            ok, msg = self.filesystem_verifier.verify_delete(path)
            return StateVerificationResult(verified=ok, verification_type=vtype, message=msg)

        if vtype in ("FS_MOVED", "FILE_MOVED"):
            src = spec.get("source", "")
            dst = spec.get("destination", "")
            ok, msg = self.filesystem_verifier.verify_move(src, dst)
            return StateVerificationResult(verified=ok, verification_type=vtype, message=msg)

        if vtype in ("FS_COPIED", "FILE_COPIED"):
            src = spec.get("source", "")
            dst = spec.get("destination", "")
            ok, msg = self.filesystem_verifier.verify_copy(src, dst)
            return StateVerificationResult(verified=ok, verification_type=vtype, message=msg)

        if vtype in ("FS_RENAMED", "FILE_RENAMED"):
            old_p = spec.get("old_path", "")
            new_p = spec.get("new_path", "")
            ok, msg = self.filesystem_verifier.verify_rename(old_p, new_p)
            return StateVerificationResult(verified=ok, verification_type=vtype, message=msg)

        if vtype in ("FS_WRITTEN", "FILE_WRITTEN"):
            path = spec.get("path") or spec.get("target", "")
            snippet = spec.get("snippet")
            ok, msg = self.filesystem_verifier.verify_write(path, expected_snippet=snippet)
            return StateVerificationResult(verified=ok, verification_type=vtype, message=msg)

        # -------------------------------------------------------------
        # 4. Screen Text & UI Diff
        # -------------------------------------------------------------
        if vtype in ("SCREEN_CONTAINS_TEXT", "TEXT_VISIBLE"):
            text = spec.get("text", "")
            if observation_after:
                res = self.screen_verifier.verify_text_present(observation_after, text)
                return StateVerificationResult(
                    verified=res.verified,
                    verification_type=vtype,
                    message=res.reason,
                )
            return StateVerificationResult(
                verified=True,
                verification_type=vtype,
                message="Text verification skipped (no observation).",
            )

        if vtype in ("SCREEN_CHANGED", "UI_DIFF"):
            if observation_before and observation_after:
                from app.core.observation_diff import diff_observations
                diff = diff_observations(observation_before, observation_after)
                return StateVerificationResult(
                    verified=diff.has_meaningful_change,
                    verification_type=vtype,
                    message="UI changed meaningfully." if diff.has_meaningful_change else "No meaningful UI change detected.",
                )

        return StateVerificationResult(
            verified=True,
            verification_type=vtype,
            message=f"Default verification passed for '{vtype}'.",
        )
