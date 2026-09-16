import time

from app.perception.grounding import UIGrounder
from app.perception.ocr import OCR, TesseractOCR
from app.perception.screenshot import ScreenshotCapture
from app.tutoring.instruction import TutoringInstruction
from app.tutoring.overlay import HighlightOverlay
from app.verification.application_verifier import (
    ApplicationVerifier,
)
from app.verification.screen_verifier import (
    ScreenVerifier,
)
from app.voice.voice_manager import VoiceManager


class TutoringController:
    """
    Controls the interactive Show Me How experience.

    AURA never performs the requested user action in this mode.

    It:
        - gives voice guidance
        - observes the screen
        - grounds visible targets
        - highlights targets
        - detects completion
        - provides recovery guidance

    AURA does not click, type, or press keys on behalf
    of the user in Show Me How mode.
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
        screen_verifier: ScreenVerifier | None = None,
        application_verifier: ApplicationVerifier | None = None,
        grounding_threshold: float = 0.65,
    ):
        self.voice_manager = voice_manager

        self.screenshot_capture = (
            screenshot_capture
            or ScreenshotCapture()
        )

        self.ocr = (
            ocr
            or TesseractOCR()
        )

        self.grounder = (
            grounder
            or UIGrounder()
        )

        self.overlay = (
            overlay
            or HighlightOverlay()
        )

        self.poll_interval = poll_interval
        self.timeout = timeout

        self.application_verifier = (
            application_verifier
            or ApplicationVerifier()
        )

        self.screen_verifier = (
            screen_verifier
            or ScreenVerifier(
                screenshot_capture=self.screenshot_capture,
                ocr=self.ocr,
                grounder=self.grounder,
            )
        )

        self.grounding_threshold = grounding_threshold

        self._baseline_screen = None

    def run(
        self,
        instructions: list[TutoringInstruction],
    ) -> bool:
        """
        Run tutoring instructions sequentially.

        Returns True only when every tutoring step
        is completed.
        """

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
                f"\nTutoring step "
                f"{index}/{total_steps}"
            )

            completed = self._execute_instruction(
                instruction
            )

            if not completed:
                print(
                    "Tutoring step failed."
                )

                self.voice_manager.speak(
                    "I could not confirm "
                    "that you completed "
                    "the step."
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
        """
        Give the instruction and continuously observe
        until the user completes it.
        """

        instruction.attempts = 0

        if self._requires_screen_baseline(
            instruction
        ):
            self._baseline_screen = (
                self.screenshot_capture.capture()
            )

        self.voice_manager.speak(
            instruction.message
        )

        if instruction.target:
            self._highlight_target(
                instruction.target
            )

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
        """
        Continuously observe the screen until the
        expected user action is detected.
        """

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
        """Check whether the tutoring step is complete."""

        completion = instruction.completion

        if not completion:
            return False

        if "screen_contains" in completion:
            target = completion[
                "screen_contains"
            ]

            result = (
                self.screen_verifier.contains_text(
                    str(target)
                )
            )

            return result.success

        if "screen_not_contains" in completion:
            target = completion[
                "screen_not_contains"
            ]

            result = (
                self.screen_verifier.does_not_contain_text(
                    str(target)
                )
            )

            return result.success

        if "screen_changed" in completion:
            current_screen = (
                self.screenshot_capture.capture()
            )

            if self._baseline_screen is None:
                self._baseline_screen = current_screen
                return False

            return self._compare_screens(
                self._baseline_screen,
                current_screen,
            )

        if "application_running" in completion:
            process = completion[
                "application_running"
            ]

            result = (
                self.application_verifier.verify(
                    str(process)
                )
            )

            return result.success

        if "target_disappears" in completion:
            target = completion[
                "target_disappears"
            ]

            result = (
                self.screen_verifier.does_not_contain_text(
                    str(target)
                )
            )

            return result.success

        return False

    def _compare_screens(
        self,
        baseline,
        current,
    ) -> bool:
        """Compare two screenshots."""

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
                f"Screen comparison error: {error}"
            )
            return False

    def _recover_instruction(
        self,
        instruction: TutoringInstruction,
    ) -> bool:
        """Retry an instruction using its recovery policy."""

        recovery = instruction.recovery

        if not recovery:
            return False

        max_attempts = int(
            recovery.get("max_attempts", 0)
        )

        if max_attempts <= 0:
            return False

        while instruction.attempts < max_attempts:
            instruction.attempts += 1

            message = recovery.get(
                "message"
            )

            if message:
                self.voice_manager.speak(
                    str(message)
                )

            print(
                f"Recovery attempt "
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
        """Check whether screen-change detection is required."""

        return (
            "screen_changed"
            in instruction.completion
        )

    def _highlight_target(
        self,
        target: str,
    ) -> None:
        """
        Locate and highlight a target inside the
        current foreground window.

        OCR coordinates are converted from window-relative
        coordinates into absolute screen coordinates.
        """

        if self.ocr is None:
            print(
                "OCR is unavailable; "
                "cannot highlight target."
            )
            return

        try:
            window_bounds = (
                self.screenshot_capture
                .get_foreground_window_bounds()
            )

            window_x = window_bounds[0]
            window_y = window_bounds[1]

            image = (
                self.screenshot_capture
                .capture_foreground_window()
            )

            elements = self.ocr.detect_text(
                image
            )

            if not elements:
                print(
                    "No OCR elements detected "
                    "in the foreground window."
                )
                return

            result = self.grounder.ground(
                elements=elements,
                target=target,
            )

            if not result.found:
                print(
                    f"Could not find tutoring target "
                    f"in foreground window: "
                    f"{target}"
                )
                return

            if result.score < self.grounding_threshold:
                print(
                    f"Target match too weak: "
                    f"{target} "
                    f"(score={result.score:.2f})"
                )
                return

            element = result.element

            screen_x = (
                window_x
                + int(element.x)
            )

            screen_y = (
                window_y
                + int(element.y)
            )

            print(
                f"Grounded tutoring target: "
                f"{element.text} "
                f"score={result.score:.2f} "
                f"reason={result.reason}"
            )

            print(
                f"Window-relative coordinates: "
                f"({element.x}, {element.y})"
            )

            print(
                f"Screen coordinates: "
                f"({screen_x}, {screen_y})"
            )

            self.overlay.show(
                x=screen_x,
                y=screen_y,
                width=element.width,
                height=element.height,
            )

        except Exception as error:
            print(
                f"Tutoring target detection error: "
                f"{error}"
            )