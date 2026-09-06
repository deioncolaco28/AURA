import pyautogui


class KeyboardController:
    """Controls keyboard input."""

    def type_text(self, text: str, interval: float = 0.02) -> None:
        """Type text using the keyboard."""

        pyautogui.write(
            text,
            interval=interval,
        )

    def press(self, key: str) -> None:
        """Press a single key."""

        pyautogui.press(key)

    def hotkey(self, *keys: str) -> None:
        """Press a keyboard shortcut."""

        pyautogui.hotkey(*keys)