import base64
import inspect
import time
from io import BytesIO
from pathlib import Path
from numpy import ndarray
import cv2 as cv
from cv_pom.cv_pom_driver import CVPOMDriver
from PIL import Image
import numpy as np

try:
    from testui.support.logger import log_info
    from selenium.webdriver.common.actions.action_builder import ActionBuilder
    from selenium.webdriver.common.actions import interaction
    from selenium.webdriver.common.actions.pointer_input import PointerInput
except ImportError:
    pass


class TestUICVPOMDriver(CVPOMDriver):
    """CVPOMDriver adapted for Py-TestUI framework"""

    def __init__(self, model_path: Path | str, driver, **kwargs) -> None:
        """Initialize the driver

        Args:
            model_path: path to the CVPOM model
            driver: path to the TestUIDriver
        """
        super().__init__(model_path, **kwargs)
        self._driver = driver

    def _get_screenshot(self) -> ndarray:
        driver = self._driver.get_driver  # Deprecated property 1.2.1 python-testui
        if inspect.ismethod(self._driver.get_driver):
            driver = self._driver.get_driver()
        image = driver.get_screenshot_as_base64()
        sbuf = BytesIO()
        sbuf.write(base64.b64decode(str(image)))
        pimg = Image.open(sbuf)
        return cv.cvtColor(np.array(pimg), cv.COLOR_RGB2BGR)

    def _click_coordinates(self, x: int, y: int, times=1, interval=0, button="PRIMARY"):
        driver = self._driver.get_driver  # Deprecated property 1.2.1 python-testui
        if inspect.ismethod(self._driver.get_driver):
            driver = self._driver.get_driver()
        self._driver.actions().w3c_actions = ActionBuilder(
            driver,
            mouse=PointerInput(interaction.POINTER_TOUCH, "touch"),
        )

        for i in range(times):
            actions = self._driver.actions()
            actions.w3c_actions.pointer_action.move_to_location(x=x, y=y)
            actions.w3c_actions.pointer_action.click()
            actions.perform()
            time.sleep(interval)

    def _send_keys(self, keys: str):
        self._driver.actions().send_keys(keys).perform()

    def _swipe_coordinates(self, coords: tuple = None, direction: str = None):
        actions = self._driver.actions()

        if coords is not None:
            x, y, x_end, y_end = coords
        else:
            h, w, ch = self._get_screenshot().shape
            if direction.lower() == "down":
                x, y, x_end, y_end = int(w / 2), int(4 * h / 6), int(w / 2), int(2 * h / 6)
            elif direction.lower() == "up":
                x, y, x_end, y_end = int(w / 2), int(2 * h / 6), int(w / 2), int(4 * h / 6)
            elif direction.lower() == "left":
                x, y, x_end, y_end = int(w / 4), int(h / 2), int(3 * w / 4), int(h / 2)
            elif direction.lower() == "right":
                x, y, x_end, y_end = int(3 * w / 4), int(h / 2), int(w / 4), int(h / 2)
            else:
                raise Exception(f"direction has to be one of this: down, up, left, right. Was {direction}")

        if self._driver.device_udid is None:
            delta_x = x - x_end
            delta_y = y - y_end
            log_info(f"swiping deltas: {delta_x}, {delta_y}")
            actions.w3c_actions.wheel_action.scroll(delta_x=delta_x, delta_y=delta_y)
            actions.perform()
            return

        log_info(f"swiping coordinates: {x}, {y}, {x_end}, {y_end}")
        actions.w3c_actions.pointer_action.move_to_location(x=x, y=y)
        actions.w3c_actions.pointer_action.pointer_down()
        actions.w3c_actions.pointer_action.move_to_location(x=x_end, y=y_end)
        actions.w3c_actions.pointer_action.release()
        actions.perform()

    def _hover_coordinates(self, x: int, y: int):
        driver = self._driver.get_driver  # Deprecated property 1.2.1 python-testui
        if inspect.ismethod(self._driver.get_driver):
            driver = self._driver.get_driver()
        self._driver.actions().w3c_actions = ActionBuilder(
            driver,
            mouse=PointerInput(interaction.POINTER_TOUCH, "touch"),
        )

        actions = self._driver.actions()
        actions.w3c_actions.pointer_action.move_to_location(x=x, y=y)
        actions.perform()

    def _drag_drop(self, x: int, y: int, x_end: int, y_end: int, duration=0.1):
        driver = self._driver.get_driver  # Deprecated property 1.2.1 python-testui
        if inspect.ismethod(self._driver.get_driver):
            driver = self._driver.get_driver()
        self._driver.actions().w3c_actions = ActionBuilder(
            driver,
            mouse=PointerInput(interaction.POINTER_TOUCH, "touch"),
            duration=duration
        )

        actions = self._driver.actions()
        actions.w3c_actions.pointer_action.move_to_location(x=x, y=y)
        actions.w3c_actions.pointer_action.pointer_down()
        actions.w3c_actions.pointer_action.move_to_location(x=x_end, y=y_end)
        actions.w3c_actions.pointer_action.release()
        actions.perform()
