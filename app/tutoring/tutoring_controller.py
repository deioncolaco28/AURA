import time

from app.config.constants import AssistantMode
from app.intelligence.action import ActionType
from app.tutoring.overlay import HighlightOverlay
from app.tutoring.tutoring_engine import TutoringEngine


class TutoringController:
    """
    Controls the complete SHOW_ME_HOW tutoring workflow.

    The user performs the actual actions.

    AURA:
        - speaks instructions
        - observes the screen
        - highlights targets
        - waits for completion
        - verifies each step
        - marks instructions as completed

    The controller never performs the requested user action.
    """

    def __init__(
        self,
        overlay=None,
        grounder=None,
        observer=None,
        tts=None,
        voice_manager=None,
        tutoring_engine=None,
    ):
        self.overlay = overlay or HighlightOverlay()
        self.grounder = grounder
        self.observer = observer
        self.tts = tts
        self.voice_manager = voice_manager

        if tutoring_engine is not None:
            self.tutoring_engine = tutoring_engine
        else:
            self.tutoring_engine = TutoringEngine(
                voice_manager=self.voice_manager,
                grounder=grounder,
                overlay=self.overlay,
            )

        if self.grounder is None:
            self.grounder = getattr(
                self.tutoring_engine,
                "grounder",
                None,
            )

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
        """
        Execute a complete SHOW_ME_HOW Task.
        """

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
            print(
                f"\nTutoring step "
                f"{index}/{total_steps}"
            )

            success = self._run_single_instruction(
                instruction
            )

            instruction.completed = success

            if success:
                print(
                    f"Step {index} completed."
                )
            else:
                print(
                    f"Step {index} failed."
                )

                completed = False
                break

        return completed

    def _run_actions(self, actions):
        """
        Compatibility path for callers that provide
        Action objects instead of TutoringInstruction objects.
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

    def _run_single_instruction(self, instruction):
        """
        Run one tutoring instruction.

        The controller owns speech.

        TutoringEngine is used only for:
            screenshot
            OCR
            grounding
            highlighting
        """

        action_type = getattr(
            instruction,
            "action_type",
            None,
        )

        parameters = getattr(
            instruction,
            "parameters",
            {},
        ) or {}

        completion = getattr(
            instruction,
            "completion",
            {},
        ) or {}

        target = getattr(
            instruction,
            "target",
            None,
        )

        message = getattr(
            instruction,
            "message",
            "",
        )

        # --------------------------------------------------------------
        # Capture baseline before a manual screen-changing action.
        # --------------------------------------------------------------

        baseline = None

        if (
            action_type == ActionType.PRESS_KEY
            and completion.get("screen_changed")
        ):
            baseline = self._screen_signature()

        # --------------------------------------------------------------
        # Speak instruction exactly once.
        # --------------------------------------------------------------

        self._speak(message)

        # --------------------------------------------------------------
        # Highlight target when applicable.
        # --------------------------------------------------------------

        if target:
            highlighted = (
                self.tutoring_engine.highlight_target(
                    target
                )
            )

            if not highlighted:
                print(
                    f"Could not highlight target: "
                    f"{target}"
                )

        # --------------------------------------------------------------
        # SPEAK requires no user action.
        # --------------------------------------------------------------

        if action_type == ActionType.SPEAK:
            return True

        # --------------------------------------------------------------
        # PRESS KEY
        # --------------------------------------------------------------

        if action_type == ActionType.PRESS_KEY:
            return self._wait_for_press_key_completion(
                completion,
                baseline,
            )

        # --------------------------------------------------------------
        # TYPE TEXT
        # --------------------------------------------------------------

        if action_type == ActionType.TYPE_TEXT:
            text = parameters.get(
                "text",
                "",
            )

            return self._wait_for_text(
                text
            )

        # --------------------------------------------------------------
        # CLICK
        # --------------------------------------------------------------

        if action_type == ActionType.CLICK:
            return self._wait_for_click_completion(
                completion,
                target,
            )

        # --------------------------------------------------------------
        # WAIT
        # --------------------------------------------------------------

        if action_type == ActionType.WAIT:
            seconds = float(
                parameters.get(
                    "seconds",
                    1.0,
                )
            )

            time.sleep(seconds)
            return True

        # --------------------------------------------------------------
        # Unknown instruction.
        # --------------------------------------------------------------

        print(
            f"Unsupported tutoring instruction: "
            f"{action_type}"
        )

        return False

    # ------------------------------------------------------------------
    # ACTION COMPATIBILITY
    # ------------------------------------------------------------------

    def _execute_action(self, action):
        """
        Compatibility handler for raw Action objects.
        """

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
                or f"Please type {text}."
            )

            self._wait_for_text(text)
            return

        if action_type == ActionType.CLICK:
            target = action.target

            if target:
                self.tutoring_engine.highlight_target(
                    target
                )

            self._speak(
                action.description
                or "Please click the highlighted target."
            )

            return

        if action_type == ActionType.WAIT:
            seconds = float(
                action.parameters.get(
                    "seconds",
                    1.0,
                )
            )

            time.sleep(seconds)
            return

    # ------------------------------------------------------------------
    # COMPLETION CHECKS
    # ------------------------------------------------------------------

    def _wait_for_press_key_completion(
        self,
        completion,
        baseline,
        timeout=8.0,
    ):
        if not completion.get("screen_changed"):
            return True

        if baseline is None:
            baseline = self._screen_signature()

        start = time.time()

        while time.time() - start < timeout:
            current = self._screen_signature()

            if (
                current is not None
                and baseline is not None
                and current != baseline
            ):
                print(
                    "Screen change detected."
                )
                return True

            time.sleep(0.5)

        print(
            "Timed out waiting for screen change."
        )

        return False

    def _wait_for_text(
        self,
        text,
        timeout=8.0,
    ):
        if not text:
            return True

        start = time.time()

        while time.time() - start < timeout:
            elements = self._get_screen_elements()

            if elements and self.grounder is not None:
                result = self.grounder.ground(
                    elements,
                    text,
                )

                if result.found:
                    print(
                        f"Screen text detected: "
                        f"{text} "
                        f"(score={result.score:.2f})"
                    )
                    return True

            time.sleep(0.5)

        print(
            f"Timed out waiting for screen text: "
            f"{text}"
        )

        return False

    def _wait_for_click_completion(
        self,
        completion,
        target,
        timeout=8.0,
    ):
        verification_type = completion.get(
            "type"
        )

        # --------------------------------------------------------------
        # Application running
        # --------------------------------------------------------------

        if verification_type == "APPLICATION_RUNNING":
            process = completion.get(
                "process"
            )

            processes = completion.get(
                "processes"
            )

            if process:
                expected_processes = [
                    process
                ]
            elif processes:
                expected_processes = list(
                    processes
                )
            else:
                expected_processes = []

            if not expected_processes:
                return True

            start = time.time()

            while time.time() - start < timeout:
                if self._process_running(
                    expected_processes
                ):
                    print(
                        "Application detected: "
                        f"{expected_processes}"
                    )
                    return True

                time.sleep(0.5)

            print(
                "Timed out waiting for application: "
                f"{expected_processes}"
            )

            return False

        # --------------------------------------------------------------
        # Screen text verification
        # --------------------------------------------------------------

        if verification_type == "SCREEN_CONTAINS_TEXT":
            expected = completion.get(
                "text"
            )

            return self._wait_for_text(
                expected
            )

        # --------------------------------------------------------------
        # No explicit verification.
        # --------------------------------------------------------------

        if target:
            time.sleep(0.5)

        return True

    # ------------------------------------------------------------------
    # SCREEN OBSERVATION
    # ------------------------------------------------------------------

    def _get_screen_elements(self):
        """
        Get OCR elements.

        Prefer the explicitly supplied observer.

        Otherwise use the TutoringEngine's
        screenshot + OCR pipeline.
        """

        if self.observer is not None:
            try:
                result = self.observer.observe()

                if result is None:
                    return []

                if isinstance(result, list):
                    return result

                elements = getattr(
                    result,
                    "elements",
                    None,
                )

                if elements is not None:
                    return elements

            except Exception as exc:
                print(
                    f"Screen observation failed: "
                    f"{exc}"
                )

        try:
            screenshot_capture = getattr(
                self.tutoring_engine,
                "screenshot_capture",
                None,
            )

            ocr = getattr(
                self.tutoring_engine,
                "ocr",
                None,
            )

            if (
                screenshot_capture is None
                or ocr is None
            ):
                return []

            image = screenshot_capture.capture()

            return ocr.detect_text(
                image
            )

        except Exception as exc:
            print(
                f"Tutoring OCR failed: "
                f"{exc}"
            )

            return []

    def _screen_signature(self):
        """
        Create a lightweight signature of the
        currently visible OCR text.
        """

        elements = self._get_screen_elements()

        if not elements:
            return None

        values = []

        for element in elements:
            text = str(
                getattr(
                    element,
                    "text",
                    "",
                )
            ).strip().lower()

            if text:
                values.append(text)

        if not values:
            return None

        return tuple(sorted(values))

    # ------------------------------------------------------------------
    # PROCESS VERIFICATION
    # ------------------------------------------------------------------

    @staticmethod
    def _process_running(processes):
        try:
            import subprocess

            result = subprocess.run(
                [
                    "tasklist",
                    "/FO",
                    "CSV",
                    "/NH",
                ],
                capture_output=True,
                text=True,
                creationflags=(
                    getattr(
                        subprocess,
                        "CREATE_NO_WINDOW",
                        0,
                    )
                ),
                check=False,
            )

            output = result.stdout.lower()

            for process in processes:
                expected = str(
                    process
                ).strip().lower()

                if expected and expected in output:
                    return True

            return False

        except Exception as exc:
            print(
                f"Process verification failed: "
                f"{exc}"
            )

            return False

    # ------------------------------------------------------------------
    # VOICE
    # ------------------------------------------------------------------

    def _speak(self, text):
        if not text:
            return

        print(
            f"AURA: {text}"
        )

        if self.tts is not None:
            try:
                self.tts.speak(text)
                return
            except Exception as exc:
                print(
                    f"TTS failed: {exc}"
                )

        if self.voice_manager is not None:
            try:
                self.voice_manager.speak(text)
            except Exception as exc:
                print(
                    f"Voice manager failed: "
                    f"{exc}"
                )