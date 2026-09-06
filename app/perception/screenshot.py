from pathlib import Path

import pyautogui


class ScreenshotCapture:
    """Captures screenshots of the computer screen."""

    def capture(self):
        """Capture the current screen."""

        return pyautogui.screenshot()

    def save(self, image, path: str) -> str:
        """Save a screenshot to disk."""

        output_path = Path(path)

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        image.save(output_path)

        return str(output_path)