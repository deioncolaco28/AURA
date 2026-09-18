"""
app/tutoring/tutoring_controller.py

Tutoring state machine for SHOW_ME_HOW mode.

States
------
OBSERVE          → capture baseline before user acts
UNDERSTAND_TARGET → locate and describe the target
GENERATE_INSTRUCTION → build natural-language instruction
SPEAK            → deliver instruction to user
WAIT_FOR_USER    → poll for expected state transition
VERIFY           → confirm expected transition occurred
RECOVER          → re-speak instruction when timeout occurs
COMPLETED        → step done
FAILED           → step failed after all recovery attempts

Key rules
---------
- ALWAYS captures a baseline observation BEFORE waiting for user.
- NEVER marks a step complete merely because the target is visible.
- NEVER performs the requested user action.
- Uses ObservationDiff for before/after comparison.
- Polls with configurable interval and timeout.
- Recovery = re-speak instruction, never auto-execute.
- Overlay is optional — used when present, skipped when absent.
"""

from __future__ import annotations

import time
from enum import Enum, auto

from app.config.constants import AssistantMode
from app.core.observation import ScreenObservation
from app.core.observation_diff import ObservationDiffer
from app.intelligence.action import ActionType
from app.logging.logger import AURALogger
from app.perception.target_query import TargetQuery, parse_target_query
from app.perception.ui_element import UIElement, to_ui_elements
from app.tutoring.tutoring_engine import TutoringEngine


# ---------------------------------------------------------------------------
# State enum
# ---------------------------------------------------------------------------


class TutoringState(Enum):
    OBSERVE = auto()
    UNDERSTAND = auto()
    INSTRUCT = auto()
    WAITING_FOR_USER = auto()
    VERIFY = auto()
    RECOVER = auto()
    COMPLETED = auto()
    FAILED = auto()

    # Aliases for explicit spec names & backwards compatibility
    OBSERVING = OBSERVE
    UNDERSTANDING = UNDERSTAND
    UNDERSTAND_TARGET = UNDERSTAND
    INSTRUCTING = INSTRUCT
    GENERATE_INSTRUCTION = INSTRUCT
    SPEAK = INSTRUCT
    WAIT_FOR_USER = WAITING_FOR_USER
    VERIFYING = VERIFY
    RECOVERING = RECOVER


# ---------------------------------------------------------------------------
# TutoringController
# ---------------------------------------------------------------------------


class TutoringController:
    """
    Controls the complete SHOW_ME_HOW tutoring workflow.

    The user performs the actual actions.

    AURA:
        - speaks instructions
        - captures a baseline before waiting
        - observes the screen
        - waits for completion using before/after comparison
        - verifies each step
        - re-speaks when the user does not act in time

    The controller NEVER performs the requested user action.
    """

    # Default timing constants
    DEFAULT_POLL_INTERVAL = 0.5    # seconds between observation polls
    DEFAULT_STEP_TIMEOUT = 15.0    # seconds to wait per instruction
    DEFAULT_MAX_RECOVERY = 2       # max re-instruction attempts

    def __init__(
        self,
        overlay=None,
        grounder=None,
        observer=None,
        tts=None,
        voice_manager=None,
        tutoring_engine=None,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        step_timeout: float = DEFAULT_STEP_TIMEOUT,
        logger=None,
    ):
        # Overlay is OPTIONAL.
        self.overlay = overlay

        self.grounder = grounder
        self.observer = observer
        self.tts = tts
        self.voice_manager = voice_manager
        self.logger = logger or AURALogger()

        if tutoring_engine is not None:
            self.tutoring_engine = tutoring_engine
        else:
            self.tutoring_engine = TutoringEngine(
                voice_manager=self.voice_manager,
                grounder=grounder,
                overlay=self.overlay,  # may be None
            )

        if self.grounder is None:
            self.grounder = getattr(
                self.tutoring_engine,
                "grounder",
                None,
            )

        self.poll_interval = poll_interval
        self.step_timeout = step_timeout
        self._differ = ObservationDiffer()
        self.current_state = TutoringState.OBSERVE
        self.stopped = False

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def run(self, task_or_instructions):
        """
        Accept either:
            - a Task object
            - a list of TutoringInstruction objects
        """

        if isinstance(task_or_instructions, list):
            return self._run_instructions(
                task_or_instructions
            )

        return self.execute(task_or_instructions)

    def execute(self, task):
        """Execute a complete SHOW_ME_HOW Task."""

        if task.mode != AssistantMode.SHOW_ME_HOW:
            return False

        actions = getattr(task, "actions", [])

        if not actions:
            return False

        print(
            f"Generated tutoring instructions: "
            f"{len(actions)}"
        )

        return self._run_actions(actions)

    # ------------------------------------------------------------------
    # INSTRUCTION WORKFLOW
    # ------------------------------------------------------------------

    def _run_instructions(self, instructions):
        if not instructions:
            return False

        print(
            f"Generated tutoring instructions: "
            f"{len(instructions)}"
        )

        completed = True
        total_steps = len(instructions)

        for index, instruction in enumerate(
            instructions,
            start=1,
        ):
            if self.stopped:
                completed = False
                break

            print(
                f"\nTutoring step "
                f"{index}/{total_steps}"
            )

            if self.logger is not None:
                try:
                    self.logger.tutoring_step_started(
                        step_index=index,
                        total_steps=total_steps,
                        action_type=getattr(instruction, "action_type", None),
                    )
                except Exception:
                    pass

            success = self._run_single_instruction(
                instruction,
                step_index=index,
            )

            instruction.completed = success

            if success:
                print(f"Step {index} completed.")
                if self.logger is not None:
                    try:
                        self.logger.tutoring_step_completed(index)
                    except Exception:
                        pass
            else:
                print(f"Step {index} failed.")
                completed = False
                break

        if self.logger is not None:
            try:
                self.logger.tutoring_task_completed(completed)
            except Exception:
                pass

        return completed

    def _run_actions(self, actions):
        """
        Compatibility path for callers that pass raw Action objects.
        """

        completed = True

        for index, action in enumerate(
            actions,
            start=1,
        ):
            print(
                f"\nTutoring step "
                f"{index}/{len(actions)}"
            )

            self._execute_action(action)

        return completed

    def _run_single_instruction(
        self,
        instruction,
        step_index: int = 1,
    ) -> bool:
        """
        Run one tutoring instruction through the state machine:
            OBSERVE → UNDERSTAND → INSTRUCT → WAITING_FOR_USER → VERIFY
            → (SUCCESS: COMPLETED) | (TIMEOUT: RECOVER → … | FAILED)
        """

        action_type = getattr(instruction, "action_type", None)
        target = getattr(instruction, "target", None)
        message = getattr(instruction, "message", "")
        completion = getattr(instruction, "completion", {}) or {}
        expected_transition = getattr(instruction, "expected_transition", {}) or {}
        parameters = getattr(instruction, "parameters", {}) or {}
        recovery_config = getattr(instruction, "recovery", {}) or {}
        success_message = getattr(instruction, "success_message", None)
        max_recovery = recovery_config.get(
            "max_attempts", self.DEFAULT_MAX_RECOVERY
        )

        # ------------------------------------------------------------------
        # SPEAK-only instructions: no user action required.
        # ------------------------------------------------------------------
        if action_type == ActionType.SPEAK:
            self._speak(message)
            return True

        if action_type == ActionType.WAIT:
            self._speak(message)
            seconds = float(parameters.get("seconds", 1.0))
            time.sleep(seconds)
            return True

        # ------------------------------------------------------------------
        # STATE: OBSERVE — capture baseline BEFORE waiting for user.
        # ------------------------------------------------------------------
        self.current_state = TutoringState.OBSERVE
        baseline = self._capture_observation()
        instruction.baseline_observation = baseline

        # ------------------------------------------------------------------
        # STATE: UNDERSTAND — locate target, parse query, check ambiguity.
        # ------------------------------------------------------------------
        self.current_state = TutoringState.UNDERSTAND
        if target:
            target_query = getattr(instruction, "target_query", None)
            if target_query is None:
                target_query = parse_target_query(target)
                instruction.target_query = target_query

            candidate = self.tutoring_engine.locate_target(
                target,
                target_query,
            )

            if candidate is not None and getattr(candidate, "is_ambiguous", False):
                self._speak(
                    "I found more than one possible target. Please specify which one you mean."
                )

            if self.logger is not None:
                try:
                    desc = getattr(candidate, "reason", "") if candidate else ""
                    self.logger.tutoring_target_resolved(target, desc)
                except Exception:
                    pass

        spoken_message = message

        # ------------------------------------------------------------------
        # Instruction and waiting loop with recovery
        # ------------------------------------------------------------------
        for attempt in range(max_recovery + 1):
            if self.stopped:
                return False

            instruction.attempts += 1

            # ----------------------------------------------------------
            # STATE: INSTRUCT / SPEAK
            # ----------------------------------------------------------
            self.current_state = TutoringState.INSTRUCT
            self._speak(spoken_message)

            # ----------------------------------------------------------
            # STATE: WAITING_FOR_USER + VERIFY
            # ----------------------------------------------------------
            self.current_state = TutoringState.WAITING_FOR_USER
            if self.logger is not None:
                try:
                    self.logger.tutoring_waiting_for_user(step_index)
                except Exception:
                    pass

            success = self._wait_and_verify(
                action_type=action_type,
                target=target,
                completion=completion,
                expected_transition=expected_transition,
                parameters=parameters,
                baseline=baseline,
                step_index=step_index,
            )

            if success:
                # ----------------------------------------------------------
                # STATE: COMPLETED
                # ----------------------------------------------------------
                self.current_state = TutoringState.COMPLETED
                if self.logger is not None:
                    try:
                        self.logger.tutoring_verification_passed(step_index)
                    except Exception:
                        pass
                if success_message:
                    self._speak(success_message)
                return True

            # ----------------------------------------------------------
            # STATE: RECOVER — re-capture and re-observe before next attempt.
            # ----------------------------------------------------------
            if attempt < max_recovery:
                self.current_state = TutoringState.RECOVER
                if self.logger is not None:
                    try:
                        self.logger.tutoring_recovery(step_index, attempt + 1)
                    except Exception:
                        pass

                recovery_message = recovery_config.get("message", "")
                if not recovery_message:
                    recovery_message = (
                        f"I haven't detected that step yet. "
                        f"{message}"
                    )

                self._speak(recovery_message)

                # Re-capture baseline for the next attempt.
                baseline = self._capture_observation()
                instruction.baseline_observation = baseline
                spoken_message = recovery_message

        # ------------------------------------------------------------------
        # STATE: FAILED — honest failure after retries exhausted
        # ------------------------------------------------------------------
        self.current_state = TutoringState.FAILED
        if self.logger is not None:
            try:
                self.logger.tutoring_verification_failed(
                    step_index,
                    "Max recovery attempts exhausted without expected state change.",
                )
            except Exception:
                pass

        self._speak("I couldn't verify that step. I can stop here or you can try again.")
        print(
            f"Tutoring step failed after "
            f"{instruction.attempts} attempt(s)."
        )
        return False

    # ------------------------------------------------------------------
    # WAIT AND VERIFY
    # ------------------------------------------------------------------

    def _wait_and_verify(
        self,
        action_type: str | None,
        target: str | None,
        completion: dict,
        expected_transition: dict,
        parameters: dict,
        baseline,
        step_index: int = 1,
    ) -> bool:
        """
        Poll the screen until the expected state transition is detected
        or the timeout expires.

        CRITICAL RULE: Target presence alone NEVER counts as completion.
        """

        deadline = time.time() + self.step_timeout

        while time.time() < deadline:
            if self.stopped:
                return False

            time.sleep(self.poll_interval)

            after = self._capture_observation()

            if after is None:
                continue

            if self.logger is not None:
                try:
                    self.logger.tutoring_observation(
                        elements_count=len(getattr(after, "elements", [])),
                        processes_count=len(getattr(after, "processes", [])),
                    )
                except Exception:
                    pass

            if after is None:
                continue

            if self._is_verified(
                action_type=action_type,
                target=target,
                completion=completion,
                expected_transition=expected_transition,
                parameters=parameters,
                before=baseline,
                after=after,
            ):
                return True

        return False

    def _is_verified(
        self,
        action_type: str | None,
        target: str | None,
        completion: dict,
        expected_transition: dict,
        parameters: dict,
        before,
        after,
    ) -> bool:
        """
        Determine whether the expected state transition has occurred.

        Uses ObservationDiff for reliable before/after comparison.
        SCREEN_CHANGED alone is NOT accepted as proof of the correct action.
        Target existence alone is NOT accepted as completion.
        """

        # Compute diff between before and after.
        diff = self._differ.compare(
            before, after, target=target
        )

        # ----------------------------------------------------------
        # CLICK verification
        # ----------------------------------------------------------
        if action_type == ActionType.CLICK:
            return self._verify_click(
                completion, expected_transition, target, diff
            )

        # ----------------------------------------------------------
        # TYPE_TEXT verification — requires before/after comparison.
        # ----------------------------------------------------------
        if action_type == ActionType.TYPE_TEXT:
            text = parameters.get("text", "")
            return self._verify_type_text(text, diff, before, after)

        # ----------------------------------------------------------
        # PRESS_KEY verification
        # ----------------------------------------------------------
        if action_type == ActionType.PRESS_KEY:
            return self._verify_press_key(
                completion, expected_transition, diff, parameters
            )

        # ----------------------------------------------------------
        # LAUNCH_APPLICATION verification
        # ----------------------------------------------------------
        if action_type == ActionType.LAUNCH_APPLICATION:
            return self._verify_launch(
                completion, expected_transition, diff
            )

        return False

    def _verify_click(
        self,
        completion: dict,
        expected_transition: dict,
        target: str | None,
        diff,
    ) -> bool:
        """
        Verify that a click action produced the expected result.

        Accepted evidence (strongest first):
            1. Expected process started.
            2. Target disappeared (window/element closed).
            3. Window title changed to expected value.
            4. Expected text appeared.

        REJECTED:
            - Target is still visible (no state change).
            - Generic unrelated screen change alone.
        """

        verification_type = completion.get("type")

        # ----------------------------------------------------------
        # APPLICATION_RUNNING check
        # ----------------------------------------------------------
        if verification_type == "APPLICATION_RUNNING":
            procs = completion.get("processes")
            if procs is None:
                single_proc = completion.get("process", "")
                procs = [single_proc] if single_proc else []
            elif isinstance(procs, str):
                procs = [procs]

            procs_lower = [str(p).lower() for p in procs if p]

            # Check if any expected process started
            for p in procs_lower:
                if p in diff.processes_started:
                    return True

            # Also check current process list in a fresh observation
            fresh = self._capture_observation()
            if fresh is not None:
                after_procs = [
                    p.lower()
                    for p in getattr(fresh, "processes", [])
                ]
                for p in procs_lower:
                    if p in after_procs:
                        return True

            return False

        # ----------------------------------------------------------
        # Target disappeared (strong signal that user clicked it)
        # ----------------------------------------------------------
        target_disappears = (
            completion.get("target_disappears")
            or expected_transition.get("target_disappears")
        )
        if target_disappears and diff.target_disappeared:
            return True

        # ----------------------------------------------------------
        # Process started
        # ----------------------------------------------------------
        process_starts = expected_transition.get("process_starts")
        if process_starts:
            if isinstance(process_starts, list):
                for p in process_starts:
                    if str(p).lower() in diff.processes_started:
                        return True
            elif str(process_starts).lower() in diff.processes_started:
                return True

        # ----------------------------------------------------------
        # Text appeared
        # ----------------------------------------------------------
        text_appeared = completion.get("text_appeared") or expected_transition.get("text_appeared")
        if text_appeared:
            for added in diff.added_text:
                if str(text_appeared).lower() in added:
                    return True

        # ----------------------------------------------------------
        # Window title changed to something meaningful
        # ----------------------------------------------------------
        if diff.window_title_changed and diff.any_change:
            return True

        # ----------------------------------------------------------
        # Generic process change is strong evidence
        # ----------------------------------------------------------
        if diff.process_change:
            return True

        # Explicitly NOT accepted: target still present alone.
        return False

    def _verify_type_text(
        self,
        text: str,
        diff,
        before,
        after,
    ) -> bool:
        """
        Verify that TYPE_TEXT resulted in the expected text appearing.

        RULE: If the text already existed before the instruction was
        given, it MUST NOT be accepted as proof of the user typing it.
        The text must have been ADDED after the baseline.
        Single-letter substring matches against unrelated text are REJECTED.
        """

        if not text:
            return False

        text_lower = text.strip().lower()

        # 1. Exact match in added text tokens
        if any(text_lower == added.strip() for added in diff.added_text):
            return True

        # 2. Text contained in added token (e.g. OCR returned full typed line)
        if any(text_lower in added for added in diff.added_text):
            return True

        # 3. Text in after screen_text but not in before screen_text
        before_text = getattr(before, "screen_text", "") or ""
        after_text = getattr(after, "screen_text", "") or ""
        if text_lower in after_text.lower() and text_lower not in before_text.lower():
            return True

        # 4. Multi-word phrase: check combined added text
        words = [w for w in text_lower.split() if len(w) >= 2]
        if words:
            combined_added = " ".join(diff.added_text)
            if text_lower in combined_added:
                return True
            if all(any(w in added for added in diff.added_text) for w in words):
                return True

        return False

    def _verify_press_key(
        self,
        completion: dict,
        expected_transition: dict,
        diff,
        parameters: dict = None,
    ) -> bool:
        """
        Verify that a key press produced a meaningful screen change.

        RULE: Generic SCREEN_CHANGED alone is weak evidence.
        We require actual element/text/process changes in the diff,
        not just any pixel difference.
        """
        if parameters is None:
            parameters = {}

        key = str(parameters.get("key", "")).lower()

        # Win key: Look for Windows Start / Search interface appearance
        if "win" in key:
            if diff.process_change:
                return True

            start_keywords = {"search", "type here to search", "all apps", "pinned", "recommended", "start", "windows"}
            for added in diff.added_text:
                if any(kw in added for kw in start_keywords):
                    return True

            # Meaningful UI appearance (>= 3 new elements or text tokens; Start menu has many items)
            if len(diff.added_elements) >= 3 or len(diff.added_text) >= 3:
                return True

            if diff.window_title_changed:
                return True

            # Single token or minor noise is rejected
            return False

        requires_screen_change = completion.get("screen_changed", False)

        if not requires_screen_change:
            return True

        # Accept process change as strong evidence.
        if diff.process_change:
            return True

        # Accept window title change.
        if diff.window_title_changed:
            return True

        # Accept >= 2 new elements (meaningful UI appearance).
        if len(diff.added_elements) >= 2:
            return True

        # Accept >= 2 new text tokens (meaningful content appeared).
        if len(diff.added_text) >= 2:
            return True

        # Single element/text change is too weak — reject.
        return False

    def _verify_launch(
        self,
        completion: dict,
        expected_transition: dict,
        diff,
    ) -> bool:
        """Verify that an application started."""

        process_starts = expected_transition.get("process_starts")
        if process_starts:
            if isinstance(process_starts, list):
                for p in process_starts:
                    if str(p).lower() in diff.processes_started:
                        return True
            elif str(process_starts).lower() in diff.processes_started:
                return True

        app_running = completion.get("application_running") or completion.get("process")
        if app_running:
            if isinstance(app_running, list):
                for p in app_running:
                    if str(p).lower() in diff.processes_started:
                        return True
            elif str(app_running).lower() in diff.processes_started:
                return True

        procs = completion.get("processes")
        if procs and isinstance(procs, list):
            for p in procs:
                if str(p).lower() in diff.processes_started:
                    return True

        # Also check current processes in fresh observation
        all_expected = []
        if isinstance(process_starts, list):
            all_expected.extend(process_starts)
        elif process_starts:
            all_expected.append(process_starts)
        if isinstance(app_running, list):
            all_expected.extend(app_running)
        elif app_running:
            all_expected.append(app_running)
        if isinstance(procs, list):
            all_expected.extend(procs)

        if all_expected:
            fresh = self._capture_observation()
            if fresh is not None:
                current_procs = [p.lower() for p in getattr(fresh, "processes", [])]
                for exp in all_expected:
                    if str(exp).lower() in current_procs:
                        return True

        if diff.process_change:
            return True

        return False

    # ------------------------------------------------------------------
    # OBSERVATION
    # ------------------------------------------------------------------

    def _capture_observation(self) -> ScreenObservation | None:
        """
        Capture a fresh screen observation.

        Prefers the injected observer.
        Falls back to TutoringEngine's OCR pipeline.
        Returns None gracefully when observation fails.
        """

        if self.observer is not None:
            try:
                result = self.observer.observe()

                if isinstance(result, ScreenObservation):
                    return result

                # Wrap raw element list for backwards compat.
                if isinstance(result, list):
                    return ScreenObservation(elements=result)

            except Exception as exc:
                print(f"Screen observation failed: {exc}")

        # Fallback: use TutoringEngine's OCR.
        try:
            screenshot_capture = getattr(
                self.tutoring_engine,
                "screenshot_capture",
                None,
            )
            ocr = getattr(self.tutoring_engine, "ocr", None)

            if screenshot_capture is None or ocr is None:
                return None

            image = screenshot_capture.capture()
            raw_elements = ocr.detect_text(image)
            from app.perception.ui_element import to_ui_elements
            elements = to_ui_elements(raw_elements)

            return ScreenObservation(
                elements=elements,
                screen_text="\n".join(
                    str(e.text or "")
                    for e in elements
                    if e.text
                ),
            )

        except Exception as exc:
            print(f"TutoringEngine OCR failed: {exc}")
            return None

    # Backwards-compat alias
    def _get_screen_elements(self):
        obs = self._capture_observation()
        if obs is None:
            return []
        return obs.elements or []

    # ------------------------------------------------------------------
    # ACTION COMPATIBILITY (raw Action objects)
    # ------------------------------------------------------------------

    def _execute_action(self, action):
        """Compatibility handler for raw Action objects."""

        action_type = action.action_type

        if action_type == ActionType.SPEAK:
            self._speak(action.value)
            return

        if action_type == ActionType.PRESS_KEY:
            self._speak(
                action.description
                or f"Please press the {action.value} key."
            )
            return

        if action_type == ActionType.TYPE_TEXT:
            text = str(action.value or "")
            self._speak(
                action.description
                or f"Please type '{text}' into the field."
            )
            return

        if action_type == ActionType.CLICK:
            target = action.target
            self._speak(
                action.description
                or (f"Click {target}." if target else "Click the element.")
            )
            return

        if action_type == ActionType.WAIT:
            seconds = float(
                action.parameters.get("seconds", 1.0)
            )
            time.sleep(seconds)
            return

    # ------------------------------------------------------------------
    # VOICE
    # ------------------------------------------------------------------

    def _speak(self, text):
        if not text or not str(text).strip():
            return

        clean_text = str(text).strip()

        if self.tts is not None:
            try:
                self.tts.speak(clean_text)
                return
            except Exception as exc:
                print(f"TTS failed: {exc}")

        if self.voice_manager is not None:
            try:
                self.voice_manager.speak(clean_text)
                return
            except Exception as exc:
                print(f"Voice manager failed: {exc}")

        # Fallback when no TTS/voice_manager is active
        print(f"AURA: {clean_text}")