from pathlib import Path

import pyautogui


class ScreenshotCapture:
    """
    Captures screenshots of the computer screen.

    The default capture() method captures the full screen.

    On Windows, capture_foreground_window() can capture only
    the currently active window. This is useful for tutoring
    and UI grounding because unrelated applications visible
    elsewhere on the desktop are excluded.
    """

    def capture(self):
        """Capture the current full screen."""

        return pyautogui.screenshot()

    def capture_foreground_window(self):
        """
        Capture the currently active foreground window.

        Returns:
            A PIL Image containing the foreground window.

        Raises:
            RuntimeError: if the foreground window cannot
                          be identified or captured.
        """

        try:
            import ctypes
            from PIL import ImageGrab

            user32 = ctypes.windll.user32

            hwnd = user32.GetForegroundWindow()

            if not hwnd:
                raise RuntimeError(
                    "Could not identify the foreground window."
                )

            rect = ctypes.wintypes.RECT()

            if not user32.GetWindowRect(
                hwnd,
                ctypes.byref(rect),
            ):
                raise RuntimeError(
                    "Could not determine foreground window bounds."
                )

            left = rect.left
            top = rect.top
            right = rect.right
            bottom = rect.bottom

            if right <= left or bottom <= top:
                raise RuntimeError(
                    "Foreground window has invalid dimensions."
                )

            return ImageGrab.grab(
                bbox=(
                    left,
                    top,
                    right,
                    bottom,
                )
            )

        except AttributeError as error:
            raise RuntimeError(
                "Foreground-window capture is only supported "
                "on Windows."
            ) from error

        except Exception as error:
            raise RuntimeError(
                f"Foreground-window capture failed: {error}"
            ) from error

    def get_foreground_window_bounds(self):
        """
        Return the screen coordinates of the foreground window.

        Returns:
            Tuple:
                (x, y, width, height)

        Raises:
            RuntimeError: if the foreground window cannot
                          be identified.
        """

        try:
            import ctypes

            user32 = ctypes.windll.user32

            hwnd = user32.GetForegroundWindow()

            if not hwnd:
                raise RuntimeError(
                    "Could not identify the foreground window."
                )

            rect = ctypes.wintypes.RECT()

            if not user32.GetWindowRect(
                hwnd,
                ctypes.byref(rect),
            ):
                raise RuntimeError(
                    "Could not determine foreground window bounds."
                )

            width = rect.right - rect.left
            height = rect.bottom - rect.top

            if width <= 0 or height <= 0:
                raise RuntimeError(
                    "Foreground window has invalid dimensions."
                )

            return (
                rect.left,
                rect.top,
                width,
                height,
            )

        except AttributeError as error:
            raise RuntimeError(
                "Foreground-window detection is only supported "
                "on Windows."
            ) from error

        except Exception as error:
            raise RuntimeError(
                f"Foreground-window detection failed: {error}"
            ) from error

    def save(self, image, path: str) -> str:
        """Save a screenshot to disk."""

        output_path = Path(path)

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        image.save(output_path)

        return str(output_path)