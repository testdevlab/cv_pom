from __future__ import annotations
import time
import numpy as np

from typing import Callable
from abc import ABC, abstractmethod
from pathlib import Path
from cv_pom.cv_pom import POM, POMElement

empty_pom_element = POMElement("", "", (0, 0), (0, 0), (0, 0), (0, 0, 0, 0), 0, {})


class CVPOMDriverElement(POMElement):
    """This class extends POMElement by adding methods for interractions"""

    def __init__(self, element: POMElement, query: dict, driver: "CVPOMDriver") -> None:
        super().__init__(**element.as_dict())  # Init POMElement part (parent class)
        self._query = query
        self._driver = driver

    def click(self, timeout=10) -> CVPOMDriverElement:
        """Click in the center of an element.

        Will wait for element to be visible first.

        Args:
            timeout: Max wait time in seconds. Defaults to 10.

        Returns:
            CVPOMDriverElement
        """
        el = self.wait_visible(timeout)
        x, y = self.center
        el._driver._click_coordinates(x, y)

        return el

    def wait_visible(self, timeout=10) -> CVPOMDriverElement:
        """Wait until element is visible

        Args:
            timeout: Max wait time in seconds. Defaults to 10.

        Returns:
            CVPOMDriverElement
        """
        elements: list[CVPOMDriverElement] = self._driver.wait_until(
            lambda: self._driver.elements(self._query),
            lambda els: len(els),
            f"Element '{self._query}' not found after {timeout}s",
            timeout
        )

        return elements[0]

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

        return self

    def send_keys(self, keys: str) -> CVPOMDriverElement:
        """Send keys.

        Will wait for element to be visible first.

        Args:
            keys: Key sequence (string) to send

        Returns:
            CVPOMDriverElement
        """
        el = self.wait_visible()
        el.click()  # Focus the input element
        el._driver._send_keys(keys)

        return el

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
    def _click_coordinates(self, x: int, y: int):
        pass

    @abstractmethod
    def _send_keys(self, keys: str):
        pass

    @abstractmethod
    def _swipe_coordinates(self, coords: tuple = None, direction: str = None):
        pass
