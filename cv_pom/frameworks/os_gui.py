from pathlib import Path
from cv_pom.cv_pom_driver import CVPOMDriver
import numpy as np
import cv2 as cv
from PIL import Image
try:
    import pyautogui
except ImportError:
    pass


class DesktopCVPOMDriver(CVPOMDriver):
    """CVPOMDriver adapted for PyAutoGUI framework"""

    def __init__(self, model_path: Path | str, **kwargs) -> None:
        """Initialize the driver

        Args:
            model_path: path to the CVPOM model
            driver: path to the TestUIDriver
        """
        super().__init__(model_path, **kwargs)
        self.resize = 1
        if kwargs["resize"]:
            self.resize = kwargs["resize"]

    def _get_screenshot(self) -> np.ndarray:
        screenshot = pyautogui.screenshot()
        width, height = screenshot.size
        screenshot = screenshot.resize((width // 2, height // 2), Image.LANCZOS)
        pimg = np.array(screenshot)
        return cv.cvtColor(np.array(pimg), cv.COLOR_RGB2BGR)

    def _click_coordinates(self, x: int, y: int):
        pyautogui.click(x, y)

    def _send_keys(self, keys: str):
        pyautogui.write(keys)

    def _swipe_coordinates(self, coords: tuple = None, direction: str = None):
        if coords:
            print("Coordinates scroll not supported")
        if direction == 'up':
            pyautogui.scroll(1)
        elif direction == 'down':
            pyautogui.scroll(-1)
        elif direction == 'left':
            pyautogui.hscroll(1)
        elif direction == 'right':
            pyautogui.hscroll(-1)
