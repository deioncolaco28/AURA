import time

from app.perception.grounding import UIGrounder
from app.perception.ocr import OCR, TesseractOCR
from app.perception.screenshot import ScreenshotCapture
from app.tutoring.instruction import TutoringInstruction
from app.tutoring.overlay import HighlightOverlay
from app.verification.application_verifier import ApplicationVerifier
from app.voice.voice_manager import VoiceManager


class TutoringController:
    """
    Controls the interactive SHOW_ME_HOW experience.

    AURA:
        - speaks instructions
        - observes the screen
        - detects UI targets
        - highlights targets
        - waits for the user to perform the action
        - verifies completion
        - provides recovery guidance

    AURA does NOT perform the user's requested action in tutoring mode.
    """

    def __init__(
        self,
        voice_manager: VoiceManager,
        screenshot_capture: ScreenshotCapture | None = None,
        ocr: OCR | None = None,
        grounder: UIGrounder | None = None,
        overlay: HighlightOverlay | None = None,
        poll_interval: float = 0.5,
        timeout: float = 30.0,
        application_verifier: ApplicationVerifier | None = None,
        grounding_threshold: float = 0.65,
    ):
        self.voice_manager = voice_manager
        self.screenshot_capture = (
            screenshot_capture or ScreenshotCapture()
        )
        self.ocr = ocr or TesseractOCR()
        self.grounder = grounder or UIGrounder()
        self.overlay = overlay or HighlightOverlay()

        self.poll_interval = poll_interval
        self.timeout = timeout
        self.application_verifier = (
            application_verifier or ApplicationVerifier()
        )
        self.grounding_threshold = grounding_threshold

        self._baseline_screen = None

    def run(
        self,
        instructions: list[TutoringInstruction],
    ) -> bool:
        if not instructions:
            self.voice_manager.speak(
                "There are no instructions available."
            )
            return False

        total_steps = len(instructions)

        for index, instruction in enumerate(
            instructions,
            start=1,
        ):
            print(
                f"\nTutoring step {index}/{total_steps}"
            )

            completed = self._execute_instruction(
                instruction
            )

            if not completed:
                print(
                    f"Tutoring step {index} failed."
                )

                self.voice_manager.speak(
                    "I could not confirm that "
                    "you completed this step."
                )

                self.overlay.close()
                return False

            instruction.completed = True

            print(
                f"Step {index} completed."
            )

            self.overlay.close()

            success_message = getattr(
                instruction,
                "success_message",
                None,
            )

            if success_message:
                self.voice_manager.speak(
                    success_message
                )

        return True

    def _execute_instruction(
        self,
        instruction: TutoringInstruction,
    ) -> bool:
        instruction.attempts = 0

        # Capture the current complete screen before
        # instructions that depend on a screen change.
        if self._requires_screen_baseline(instruction):
            self._baseline_screen = (
                self._capture_full_screen()
            )

        # Speak BEFORE asking the user to act.
        self.voice_manager.speak(
            instruction.message
        )

        # Highlight only after the instruction has been
        # spoken, so the user can immediately see what
        # AURA is referring to.
        if instruction.target:
            self._highlight_target(
                instruction.target
            )

        # SPEAK-only instructions are immediately complete.
        if instruction.action_type == "SPEAK":
            return True

        completed = self._wait_for_completion(
            instruction
        )

        if completed:
            return True

        return self._recover_instruction(
            instruction
        )

    def _wait_for_completion(
        self,
        instruction: TutoringInstruction,
    ) -> bool:
        start_time = time.time()

        while (
            time.time() - start_time
            < self.timeout
        ):
            self.overlay.update()

            if self._is_instruction_completed(
                instruction
            ):
                return True

            time.sleep(
                self.poll_interval
            )

        return False

    def _is_instruction_completed(
        self,
        instruction: TutoringInstruction,
    ) -> bool:
        completion = instruction.completion

        if not completion:
            return False

        if "screen_contains" in completion:
            target = str(
                completion["screen_contains"]
            )

            return self._screen_contains_text(
                target
            )

        if "screen_not_contains" in completion:
            target = str(
                completion["screen_not_contains"]
            )

            return not self._screen_contains_text(
                target
            )

        if "screen_changed" in completion:
            current_screen = (
                self._capture_full_screen()
            )

            if self._baseline_screen is None:
                self._baseline_screen = (
                    current_screen
                )
                return False

            return self._compare_screens(
                self._baseline_screen,
                current_screen,
            )

        if completion.get("type") == "APPLICATION_RUNNING":
            process = str(
                completion.get("process", "")
            )

            if not process:
                return False

            result = self.application_verifier.verify(
                process
            )

            return bool(result)

        if "application_running" in completion:
            process = str(
                completion["application_running"]
            )

            result = self.application_verifier.verify(
                process
            )

            return bool(result)

        if "target_disappears" in completion:
            target = str(
                completion["target_disappears"]
            )

            return not self._screen_contains_text(
                target
            )

        return False

    def _capture_full_screen(self):
        """
        Capture the complete desktop.

        This is intentionally used instead of
        capture_foreground_window() because Windows
        Start/Search is a shell surface and may not behave
        like a normal foreground application window.
        """
        return self.screenshot_capture.capture()

    def _screen_contains_text(
        self,
        target: str,
    ) -> bool:
        if not target or not target.strip():
            return False

        try:
            image = self._capture_full_screen()

            elements = self.ocr.detect_text(
                image
            )

            if not elements:
                return False

            result = self.grounder.ground(
                elements=elements,
                target=target,
            )

            if not result.found:
                return False

            if (
                result.score
                < self.grounding_threshold
            ):
                print(
                    f"Screen text match too weak: "
                    f"{target} "
                    f"(score={result.score:.2f})"
                )
                return False

            print(
                f"Screen text detected: "
                f"{target} "
                f"(score={result.score:.2f})"
            )

            return True

        except Exception as error:
            print(
                f"Screen text verification error: "
                f"{error}"
            )
            return False

    def _compare_screens(
        self,
        baseline,
        current,
    ) -> bool:
        try:
            from PIL import ImageChops

            difference = ImageChops.difference(
                baseline,
                current,
            )

            return (
                difference.getbbox()
                is not None
            )

        except Exception as error:
            print(
                f"Screen comparison error: "
                f"{error}"
            )
            return False

    def _recover_instruction(
        self,
        instruction: TutoringInstruction,
    ) -> bool:
        recovery = instruction.recovery

        if not recovery:
            return False

        max_attempts = int(
            recovery.get(
                "max_attempts",
                0,
            )
        )

        if max_attempts <= 0:
            return False

        while (
            instruction.attempts
            < max_attempts
        ):
            instruction.attempts += 1

            message = recovery.get(
                "message"
            )

            if message:
                self.voice_manager.speak(
                    str(message)
                )

            print(
                "Recovery attempt "
                f"{instruction.attempts}/"
                f"{max_attempts}"
            )

            self.overlay.close()

            if instruction.target:
                self._highlight_target(
                    instruction.target
                )

            if self._wait_for_completion(
                instruction
            ):
                return True

        return False

    def _requires_screen_baseline(
        self,
        instruction: TutoringInstruction,
    ) -> bool:
        return (
            "screen_changed"
            in instruction.completion
        )

    def _highlight_target(
        self,
        target: str,
    ) -> None:
        """
        Locate a tutoring target on the complete
        desktop and highlight it.

        Coordinates returned by OCR are already
        screen coordinates because the screenshot
        represents the entire screen.
        """
        if self.ocr is None:
            print(
                "OCR is unavailable; "
                "cannot highlight target."
            )
            return

        if not target or not target.strip():
            return

        try:
            image = self._capture_full_screen()

            elements = self.ocr.detect_text(
                image
            )

            print(
                f"Full-screen OCR detected "
                f"{len(elements)} element(s)."
            )

            if not elements:
                print(
                    "No OCR elements detected."
                )
                return

            result = self.grounder.ground(
                elements=elements,
                target=target,
            )

            if not result.found:
                print(
                    "Could not find tutoring "
                    f"target: {target}"
                )
                return

            if (
                result.score
                < self.grounding_threshold
            ):
                print(
                    f"Target match too weak: "
                    f"{target} "
                    f"(score={result.score:.2f})"
                )
                return

            element = result.element

            if element is None:
                print(
                    "Grounding returned no element."
                )
                return

            screen_x = int(element.x)
            screen_y = int(element.y)

            width = max(
                int(element.width),
                20,
            )

            height = max(
                int(element.height),
                20,
            )

            print(
                f"Grounded tutoring target: "
                f"{element.text} "
                f"score={result.score:.2f} "
                f"reason={result.reason}"
            )

            print(
                "Screen coordinates: "
                f"({screen_x}, {screen_y})"
            )

            print(
                "Highlight size: "
                f"{width}x{height}"
            )

            self.overlay.show(
                x=screen_x,
                y=screen_y,
                width=width,
                height=height,
            )

        except Exception as error:
            print(
                "Tutoring target detection "
                f"error: {error}"
            )