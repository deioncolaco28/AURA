"""
app/intelligence/expected_state.py

Machine-checkable expected-state representation and state comparator for AURA.
Compares postconditions against observed screen and system states.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.core.observation import ScreenObservation
    from app.core.observation_diff import ObservationDiff


@dataclass
class ExpectedState:
    """
    Structured specification of the state expected AFTER an action executes.
    """

    # Application conditions
    app_running: str | list[str] | None = None
    app_foreground: str | None = None
    app_closed: str | None = None
    window_title_contains: str | None = None

    # Browser conditions
    browser_url_contains: str | None = None
    browser_title_contains: str | None = None

    # Filesystem conditions
    file_exists: str | None = None
    folder_exists: str | None = None
    file_deleted: str | None = None
    file_moved: tuple[str, str] | None = None  # (source_path, destination_path)
    file_contains_snippet: tuple[str, str] | None = None  # (path, snippet)

    # UI / Screen conditions
    text_visible: str | list[str] | None = None
    text_absent: str | list[str] | None = None
    element_present: str | None = None
    screen_changed: bool = False

    # Metadata & Custom predicate
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StateComparisonResult:
    """Outcome of comparing ExpectedState against observed environment state."""

    success: bool
    confidence: float = 1.0
    matched_conditions: list[str] = field(default_factory=list)
    failed_conditions: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)
    unexpected_evidence: list[str] = field(default_factory=list)
    explanation: str = ""

    @property
    def is_verified(self) -> bool:
        return self.success


class StateComparator:
    """
    Compares an ExpectedState against a ScreenObservation, ObservationDiff,
    and optional system state verifiers.
    """

    def compare(
        self,
        expected: ExpectedState,
        observation: ScreenObservation | None = None,
        diff: ObservationDiff | None = None,
        system_verifier: Any = None,
    ) -> StateComparisonResult:
        """Evaluate whether the observed state matches all specified expected postconditions."""
        matched: list[str] = []
        failed: list[str] = []
        missing: list[str] = []

        # -------------------------------------------------------------
        # 1. Application Running / Foreground
        # -------------------------------------------------------------
        if expected.app_running:
            apps = [expected.app_running] if isinstance(expected.app_running, str) else expected.app_running
            running_procs = [p.lower() for p in getattr(observation, "processes", [])]
            # Also check diff
            started_procs = [p.lower() for p in (diff.processes_started if diff else [])]
            all_procs = set(running_procs + started_procs)

            for app in apps:
                app_clean = app.lower().replace(".exe", "")
                found = any(app_clean in p for p in all_procs)
                if not found and system_verifier and hasattr(system_verifier, "application_verifier"):
                    found = system_verifier.application_verifier.is_running(app)

                if found:
                    matched.append(f"app_running:{app}")
                else:
                    failed.append(f"app_running:{app}")
                    missing.append(f"Process for '{app}' not detected in running processes.")

        if expected.app_foreground:
            fg_target = expected.app_foreground.lower()
            fg_actual = (
                str(getattr(observation, "foreground_app", "") or "")
                or str(getattr(getattr(observation, "foreground_context", None), "app_name", "") or "")
            ).lower()

            if fg_target in fg_actual or (fg_actual and fg_actual in fg_target):
                matched.append(f"app_foreground:{expected.app_foreground}")
            else:
                # If diff reports foreground change or window title change matching target
                if diff and diff.window_title_changed:
                    matched.append(f"app_foreground_inferred:{expected.app_foreground}")
                else:
                    failed.append(f"app_foreground:{expected.app_foreground}")
                    missing.append(f"Foreground app is '{fg_actual}', expected '{expected.app_foreground}'.")

        # -------------------------------------------------------------
        # 2. Browser URL & Title
        # -------------------------------------------------------------
        if expected.browser_url_contains:
            url_target = expected.browser_url_contains.lower()
            current_url = str(getattr(observation, "url", "") or "").lower()
            if url_target in current_url:
                matched.append(f"browser_url_contains:{expected.browser_url_contains}")
            else:
                failed.append(f"browser_url_contains:{expected.browser_url_contains}")
                missing.append(f"Browser URL '{current_url}' did not contain '{expected.browser_url_contains}'.")

        # -------------------------------------------------------------
        # 3. Filesystem Conditions
        # -------------------------------------------------------------
        if expected.file_exists or expected.folder_exists:
            path = expected.file_exists or expected.folder_exists
            import os
            if os.path.exists(path):
                matched.append(f"fs_exists:{path}")
            else:
                failed.append(f"fs_exists:{path}")
                missing.append(f"Path '{path}' does not exist on filesystem.")

        if expected.file_deleted:
            import os
            if not os.path.exists(expected.file_deleted):
                matched.append(f"file_deleted:{expected.file_deleted}")
            else:
                failed.append(f"file_deleted:{expected.file_deleted}")
                missing.append(f"File '{expected.file_deleted}' still exists on filesystem.")

        if expected.file_moved:
            src, dst = expected.file_moved
            import os
            if not os.path.exists(src) and os.path.exists(dst):
                matched.append(f"file_moved:{src}->{dst}")
            else:
                failed.append(f"file_moved:{src}->{dst}")
                missing.append(f"Move failed: source_exists={os.path.exists(src)}, dest_exists={os.path.exists(dst)}")

        # -------------------------------------------------------------
        # 4. UI / Screen Text & Element Transitions
        # -------------------------------------------------------------
        if expected.text_visible:
            texts = [expected.text_visible] if isinstance(expected.text_visible, str) else expected.text_visible
            screen_text = str(getattr(observation, "screen_text", "") or "").lower()
            for t in texts:
                t_lower = t.lower()
                if t_lower in screen_text or (diff and any(t_lower in added.lower() for added in diff.added_text)):
                    matched.append(f"text_visible:{t}")
                else:
                    failed.append(f"text_visible:{t}")
                    missing.append(f"Text '{t}' was not visible on screen.")

        if expected.screen_changed:
            if diff and diff.has_meaningful_change:
                matched.append("screen_changed:true")
            else:
                failed.append("screen_changed:true")
                missing.append("No meaningful UI change detected between before/after observations.")

        # -------------------------------------------------------------
        # Calculate Verdict & Confidence
        # -------------------------------------------------------------
        total_conditions = len(matched) + len(failed)
        if total_conditions == 0:
            return StateComparisonResult(
                success=True,
                confidence=1.0,
                matched_conditions=[],
                explanation="No explicit postconditions defined; default success.",
            )

        success = len(failed) == 0
        confidence = len(matched) / total_conditions if total_conditions > 0 else 1.0
        explanation = (
            f"All {len(matched)} expected conditions satisfied."
            if success
            else f"Failed conditions: {', '.join(failed)}. Missing: {'; '.join(missing)}"
        )

        return StateComparisonResult(
            success=success,
            confidence=confidence,
            matched_conditions=matched,
            failed_conditions=failed,
            missing_evidence=missing,
            explanation=explanation,
        )
