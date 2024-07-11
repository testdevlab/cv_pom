from __future__ import annotations
import time
import logging
import numpy as np

from typing import Callable, Optional, Tuple
from abc import ABC, abstractmethod
from pathlib import Path
from cv_pom.cv_pom import POM, POMElement

empty_pom_element = POMElement("", "", (0, 0), (0, 0), (0, 0), (0, 0, 0, 0), 0, {})

# create logger
logger = logging.getLogger('cv_pom logger')
logger.setLevel(logging.DEBUG)
# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# create formatter
formatter = logging.Formatter('[%(asctime)s] - %(levelname)s - %(message)s')
# add formatter to ch
ch.setFormatter(formatter)
# add ch to logger
logger.addHandler(ch)


class CVPOMDriverElement(POMElement):
    """This class extends POMElement by adding methods for interactions"""

    def __init__(self, element: POMElement, query: dict, driver: "CVPOMDriver") -> None:
        super().__init__(**element.as_dict())  # Init POMElement part (parent class)
        self._query = query
        self._driver = driver

    def click(self, timeout=10, offset=(0, 0), times=1, interval=0, button="PRIMARY") -> CVPOMDriverElement:
        """Click in the center of an element.

        Will wait for element to be visible first.

        Args:
            timeout: Max wait time in seconds. Defaults to 10.
            interval: interval when click times is more than 1
            button: button to use for clicking
            times: defaults to 1, and 2 performs double click for those frameworks that allows it
            offset: Offset from the coordinates of the element (AX, AY)

        Returns:
            CVPOMDriverElement
        """
        self.wait_visible(timeout)
        x, y = self.center
        ax, ay = offset
        logger.info(
            f"action: click - element coords: {self.center} - element label: \"{self.label}\" - element attrs: {self.attrs}"
        )
        self._driver._click_coordinates(x + ax, y + ay, times, interval, button)

        return self

    def wait_visible(self, timeout=10) -> CVPOMDriverElement:
        """Wait until element is visible

        Args:
            timeout: Max wait time in seconds. Defaults to 10.

        Returns:
            CVPOMDriverElement
        """
        if self.center == (0, 0):
            elements: list[CVPOMDriverElement] = self._driver.wait_until(
                lambda: self._driver.elements(self._query),
                lambda els: len(els),
                f"Element '{self._query}' not found after {timeout}s",
                timeout
            )
            self.__init__(elements[0], self._query, self._driver)

        logger.info(
            f"action: wait_visible - element coords: {self.center} - "
            f"element label: \"{self.label}\" - element attrs: {self.attrs}"
        )

        return self

    def wait_not_visible(self, timeout=10) -> CVPOMDriverElement:
        """Wait until element is not visible

        Args:
            timeout: Max wait time in seconds. Defaults to 10.

        Returns:
            CVPOMDriverElement
        """
        self._driver.wait_until(
            lambda: self._driver.elements(self._query),
            lambda els: len(els) == 0,
            f"Element '{self._query}' still visible after {timeout}s",
            timeout
        )

        logger.info(
            f"action: wait_not_visible - element coords: {self.center} - "
            f"element label: \"{self.label}\" - element attrs: {self.attrs}"
        )

        return self

    def send_keys(self, keys: str, offset=(0, 0)) -> CVPOMDriverElement:
        """Send keys.

        Will wait for element to be visible first.

        Args:
            keys: Key sequence (string) to send
            offset: Offset from the coordinates of the element (AX, AY)

        Returns:
            CVPOMDriverElement
        """
        self.click(offset=offset)  # Focus the input element
        logger.info(
            f"action: send_keys - element coords: {self.center} - "
            f"element label: \"{self.label}\" - element attrs: {self.attrs}"
        )
        self._driver._send_keys(keys)

        return self

    def swipe(self, offset: tuple = None, el: CVPOMDriverElement = None) -> CVPOMDriverElement:
        """Swipes or scrolls using coordinates, direction or an element.

        Args:
            el: if is not None then it will scroll from the el1 to the el
            offset: if is not None then it will scroll from the el1 to the offset marked by (x, y)
        Returns:
            CVPOMDriverElement
        """
        el1 = self.wait_visible()
        if offset is not None:
            x, y = el1.center
            delta_x, delta_y = offset
            x_end, y_end = x + delta_x, y + delta_y
        else:
            x, y = el1.center
            x_end, y_end = el.wait_visible().center
        self._driver._swipe_coordinates(coords=(x, y, x_end, y_end))

        return el1

    def swipe_to(self, direction: str, limit: int = 50) -> CVPOMDriverElement:
        """Swipes or scrolls direction until it finds the element.

        Args:
            direction: if is not none then will scroll/swipe "up", "down", "left" and "right"
            limit: amount of scrolls so that it does not loop infinitely, defaults to 50
        Returns:
            CVPOMDriverElement
        """
        i = 0
        elements = self._driver.elements(self._query)
        while len(elements) == 0 and i < limit:
            self._driver._swipe_coordinates(direction=direction)
            elements = self._driver.elements(self._query)
            i += 1

        el = self.wait_visible()
        return el

    def hover(self, timeout=10, offset=(0, 0)) -> CVPOMDriverElement:
        """Hover in the center of an element.

        Will wait for element to be visible first.

        Args:
            timeout: Max wait time in seconds. Defaults to 10.
            offset: Offset from the coordinates of the element (AX, AY)

        Returns:
            CVPOMDriverElement
        """
        self.wait_visible(timeout)
        x, y = self.center
        ax, ay = offset
        logger.info(
            f"action: hover - element coords: {self.center} - element label: {self.label} - element attrs: {self.attrs}"
        )
        self._driver._hover_coordinates(x + ax, y + ay)

        return self

    def drag_drop(self,
                  end_coords: Optional[Tuple[int, int]] = None,
                  delta: Optional[Tuple[int, int]] = None,
                  duration=0.1
                  ) -> CVPOMDriverElement:
        """Drag and Drop from an element to coordinates or a delta distance in pixels.

        Will wait for element to be visible.

        Args:
            offset: Offset from the coordinates of the element (AX, AY)
            end_coords: coordinates to end (optional)
            delta: distance in pixels from the element (optional)
            duration: duration for the action to take place

        Returns:
            CVPOMDriverElement
        """
        if end_coords is None and delta is None:
            logger.error("action: drag_drop - either end_coords or delta must be specified - action not performed")
            return self

        if end_coords is None:
            self.wait_visible()
            x, y = self.center
            delta_x, delta_y = delta
            x_end, y_end = x + delta_x, y + delta_y
        else:
            self.wait_visible()
            x, y = self.center
            x_end, y_end = end_coords

        logger.info("action: drag_drop - start coords: {(x, y)} - end coords: {(x_end, y_end)}")
        self._driver._drag_drop(x, y, x_end, y_end, duration)

        return self

    def drag_drop_to(self,
                     start_coords: Optional[Tuple[int, int]] = None,
                     delta: Optional[Tuple[int, int]] = None,
                     duration=0.1
                     ) -> CVPOMDriverElement:
        """Drag and Drop from coordinates or a delta distance in pixels to an element.

        Will wait for element to be visible.

        Args:
            offset: Offset from the coordinates of the element (AX, AY)
            start_coords: coordinates to start from (optional)
            delta: distance in pixels from the element (optional)
            duration: duration for the action to take place

        Returns:
            CVPOMDriverElement
        """
        if start_coords is None and delta is None:
            logger.error("action: drag_drop - either start_coords or delta must be specified - action not performed")
            return self

        if start_coords is None:
            self.wait_visible()
            x_end, y_end = self.center
            delta_x, delta_y = delta
            x, y = x_end + delta_x, y_end + delta_y

        else:
            self.wait_visible()
            x_end, y_end = self.center
            x, y = start_coords

        logger.info(f"action: drag_drop - start coords: {(x, y)} - end coords: {(x_end, y_end)}")
        self._driver._drag_drop(x, y, x_end, y_end, duration)

        return self


class CVPOMPageDriver:
    def __init__(self, pom: POM, driver: "CVPOMDriver", **kwargs) -> None:
        self._pom = pom
        self._driver = driver
        self.kwargs = kwargs

    def element(self, query: dict) -> CVPOMDriverElement:
        elements = self._pom.get_elements(query)

        if len(elements):
            return CVPOMDriverElement(elements[0], query, self._driver)

        # Even if element wasn't found, returns an Element. It can still be used to wait.
        return CVPOMDriverElement(empty_pom_element, query, self._driver)

    def elements(self, query: dict) -> list[CVPOMDriverElement]:
        elements = self._pom.get_elements(query)

        return [CVPOMDriverElement(el, query, self._driver) for el in elements]


class CVPOMDriver(ABC):
    """Driver class used to find elements in the POM"""

    def __init__(self, model_path: Path | str, **kwargs) -> None:
        self._pom = POM(model_path)
        self.kwargs = kwargs

    def element(self, query: dict) -> CVPOMDriverElement:
        """Get a single element.

        This doesn't wait for element to be visible and will not fail.
        The returned CVPOMDriverElement object will be interactable regardless
        of the existence of the element at the time of calling this method.

        Args:
            query: Query dictionary

        Returns:
            CVPOMDriverElement
        """
        ocr = None
        if "text" in query:
            ocr = {'paragraph': False}
            if self.kwargs and self.kwargs['ocr']:
                ocr = self.kwargs['ocr']
        pom = self._pom.convert_to_cvpom(self._get_screenshot(), ocr)

        return CVPOMPageDriver(pom, self).element(query)

    def elements(self, query: dict) -> list[CVPOMDriverElement]:
        """Get a list of elements.

        Args:
            query: Query dictionary

        Returns:
            list[CVPOMDriverElement]: List of elements
        """
        ocr = None
        if "text" in query or "ocr_element" in query:
            ocr = {'paragraph': False}
            if self.kwargs and self.kwargs['ocr']:
                ocr = self.kwargs['ocr']
        pom = self._pom.convert_to_cvpom(self._get_screenshot(), ocr)

        return CVPOMPageDriver(pom, self).elements(query)

    def get_page(self) -> CVPOMPageDriver:
        """Get full page POM.

        Args:

        Returns:
            POM: full CV_POM
        """
        if self.kwargs:
            pom = self._pom.convert_to_cvpom(self._get_screenshot(), self.kwargs['ocr'])
        else:
            pom = self._pom.convert_to_cvpom(self._get_screenshot())

        return CVPOMPageDriver(pom, self)

    def wait_until(self, func: Callable, condition: Callable, error_msg: str, timeout: float):
        """Wait until conditions passes and function is not raising errors.

        Args:
            func: Function to execute
            condition: Condition that needs to be satisfied (uses return value of "func" as parameter)
            error_msg: Error message in case of failure
            timeout: Timeout in seconds

        Raises:
            Exception: Timeout

        Returns:
            Any: Whatever the given function returns
        """
        error = None
        timeout_start = time.time()
        while time.time() < timeout_start + timeout:
            try:
                error = None
                result = func()
                if condition(result):
                    return result
            except Exception as e:
                error = e

        if error:
            raise Exception(f"{error_msg}, error: {error}")
        else:
            raise Exception(f"{error_msg}")

    @abstractmethod
    def _get_screenshot(self) -> np.ndarray:
        pass

    @abstractmethod
    def _click_coordinates(self, x: int, y: int, times=1, interval=0, button="PRIMARY"):
        pass

    @abstractmethod
    def _send_keys(self, keys: str):
        pass

    @abstractmethod
    def _swipe_coordinates(self, coords: tuple = None, direction: str = None):
        pass

    @abstractmethod
    def _hover_coordinates(self, x: int, y: int):
        pass

    @abstractmethod
    def _drag_drop(self, x: int, y: int, x_end: int, y_end: int, duration=0.1):
        pass
