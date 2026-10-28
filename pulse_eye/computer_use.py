import time
import sys
from typing import Tuple, List, Optional, Union
import pyautogui

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.15


def denormalize_coordinates(
    x_norm: float,
    y_norm: float,
    screen_size: Tuple[int, int]
) -> Tuple[int, int]:
    """
    Translates normalized coordinates (0 to 1000 range, standard in VLMs like Qwen2.5-VL)
    into concrete pixel coordinates (X, Y) based on screen_size (width, height).
    """
    width, height = screen_size
    px_x = int((x_norm / 1000.0) * width)
    px_y = int((y_norm / 1000.0) * height)

    px_x = max(0, min(px_x, width - 1))
    px_y = max(0, min(px_y, height - 1))

    return px_x, px_y


def bbox_to_center_coords(
    bbox: Union[List[float], Tuple[float, float, float, float]],
    screen_size: Tuple[int, int]
) -> Tuple[int, int]:
    """
    Converts a normalized bounding box [ymin, xmin, ymax, xmax] (0-1000 scale)
    into screen pixel coordinates (X, Y) located at the exact center of the box.
    """
    ymin, xmin, ymax, xmax = bbox
    center_norm_x = (xmin + xmax) / 2.0
    center_norm_y = (ymin + ymax) / 2.0
    return denormalize_coordinates(center_norm_x, center_norm_y, screen_size)


def click_at(
    x: int,
    y: int,
    button: str = "left",
    clicks: int = 1,
    screen_size: Optional[Tuple[int, int]] = None
) -> str:
    """
    Moves mouse smoothly to (x, y) and performs clicks.
    """
    try:
        if screen_size:
            w, h = screen_size
            x = max(0, min(x, w - 1))
            y = max(0, min(y, h - 1))

        pyautogui.moveTo(x, y, duration=0.2)
        pyautogui.click(x=x, y=y, button=button, clicks=clicks)
        return f"Clicked ({button}, {clicks}x) at pixel coordinates ({x}, {y})."
    except Exception as e:
        return f"Error clicking at ({x}, {y}): {e}"


def double_click_at(x: int, y: int, screen_size: Optional[Tuple[int, int]] = None) -> str:
    return click_at(x, y, button="left", clicks=2, screen_size=screen_size)


def right_click_at(x: int, y: int, screen_size: Optional[Tuple[int, int]] = None) -> str:
    return click_at(x, y, button="right", clicks=1, screen_size=screen_size)


def move_cursor_to(x: int, y: int, screen_size: Optional[Tuple[int, int]] = None) -> str:
    try:
        if screen_size:
            w, h = screen_size
            x = max(0, min(x, w - 1))
            y = max(0, min(y, h - 1))
        pyautogui.moveTo(x, y, duration=0.2)
        return f"Moved cursor to ({x}, {y})."
    except Exception as e:
        return f"Error moving cursor to ({x}, {y}): {e}"


def drag_cursor_to(x: int, y: int, screen_size: Optional[Tuple[int, int]] = None) -> str:
    try:
        if screen_size:
            w, h = screen_size
            x = max(0, min(x, w - 1))
            y = max(0, min(y, h - 1))
        pyautogui.dragTo(x, y, duration=0.4, button="left")
        return f"Dragged cursor to ({x}, {y})."
    except Exception as e:
        return f"Error dragging cursor to ({x}, {y}): {e}"


def type_keyboard_text(text: str, interval: float = 0.03, press_enter: bool = False) -> str:
    """
    Types text into the currently focused window or element.
    """
    try:
        pyautogui.write(text, interval=interval)
        if press_enter:
            pyautogui.press("enter")
            return f"Typed '{text}' and pressed Enter."
        return f"Typed '{text}' successfully."
    except Exception as e:
        return f"Error typing text: {e}"


def press_keyboard_key(key: str) -> str:
    """
    Presses an individual key (e.g. 'enter', 'tab', 'esc', 'backspace', 'down').
    """
    try:
        pyautogui.press(key.lower())
        return f"Pressed key '{key}'."
    except Exception as e:
        return f"Error pressing key '{key}': {e}"


def send_hotkey(keys: List[str]) -> str:
    """
    Sends a key combination, e.g. ['ctrl', 'c'] or ['alt', 'tab'] or ['ctrl', 't'].
    """
    try:
        lower_keys = [k.lower().strip() for k in keys]
        pyautogui.hotkey(*lower_keys)
        return f"Triggered hotkey: {' + '.join(keys)}."
    except Exception as e:
        return f"Error sending hotkey {keys}: {e}"


def scroll_screen(amount: int = 3, direction: str = "down") -> str:
    """
    Scrolls the mouse wheel.
    direction: 'down' (negative clicks) or 'up' (positive clicks).
    """
    try:
        clicks = -abs(amount) if direction.lower() == "down" else abs(amount)
        pyautogui.scroll(clicks * 100)
        return f"Scrolled {direction} by {amount} units."
    except Exception as e:
        return f"Error scrolling {direction}: {e}"


def wait_seconds(seconds: float) -> str:
    """Pauses for UI animation or page load."""
    time.sleep(max(0.1, min(seconds, 10.0)))
    return f"Waited for {seconds} seconds."
