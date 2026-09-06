from unittest.mock import patch

from app.automation.controller import ComputerController


def test_mouse_position():
    controller = ComputerController()

    with patch(
        "app.automation.mouse.pyautogui.position"
    ) as mock_position:

        mock_position.return_value.x = 100
        mock_position.return_value.y = 200

        position = controller.mouse.get_position()

        assert position == (100, 200)


def test_type_text():
    controller = ComputerController()

    with patch(
        "app.automation.keyboard.pyautogui.write"
    ) as mock_write:

        controller.type_text("Hello")

        mock_write.assert_called_once_with(
            "Hello",
            interval=0.02,
        )


def test_press_key():
    controller = ComputerController()

    with patch(
        "app.automation.keyboard.pyautogui.press"
    ) as mock_press:

        controller.press("enter")

        mock_press.assert_called_once_with("enter")


def test_hotkey():
    controller = ComputerController()

    with patch(
        "app.automation.keyboard.pyautogui.hotkey"
    ) as mock_hotkey:

        controller.hotkey("ctrl", "c")

        mock_hotkey.assert_called_once_with(
            "ctrl",
            "c",
        )


def test_move_mouse():
    controller = ComputerController()

    with patch(
        "app.automation.mouse.pyautogui.moveTo"
    ) as mock_move:

        controller.move_mouse(100, 200)

        mock_move.assert_called_once_with(
            100,
            200,
            duration=0.2,
        )