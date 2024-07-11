# CV_POM - [![PyPI - Version](https://img.shields.io/pypi/v/cv_pom)](https://pypi.org/project/cv_pom/)

## Table of Contents

 * [Introduction](#introduction)
 * [Installation](#installation)
 * [CVPOMDrivers](#CVPOMDrivers)
   * [CV POM Driver](#cv-pom-driver)
   * [Create your own Driver](#create-your-own-driver)
 * [Drivers Already Implemented](#drivers-already-implemented)
   * [Python-TestUI Driver - Selenium & Appium](#python-testui-driver---selenium--appium)
   * [PyAutoGui Driver - Native Desktop App Automation](#pyautogui-driver---native-desktop-app-automation)
 * [CV POM Usage](#cvpom-usage)
   * [Python API](#python-api)
   * [REST API Server](#rest-api-server)
   * [As CLI](#as-cli)

## Introduction

CV POM framework provides tools to detect elements in image content and interact with them.

The framework converts any image into a page object model. This model lets you access the elements recognized in the image. Elements contain such properties as labels, coordinates and others. It's also possible to transform the elements into a JSON representation for easy integration with other tools.

## Installation

```bash
pip install cv_pom
```


## CVPOMDrivers

### CV POM Driver
CV POM Driver is built on top of CV POM and provides easy integration with any automation framework (like Selenium or Appium). The user just needs to overwrite a couple of methods of the `CVPOMDriver` class and then use it as a driver to find elements and interact with them.

Since this approach doesn't require any APIs from the application to test, it is generic for every platform/app combination, allowing the user to automate for each platform with the same APIs. It also allows the automation of workflows based on the UI representation, which validates the stylings and placement of each of the elements, which is something that most UI automation frameworks lack.


### Create your own Driver

First, overwrite two methods of CVPOMDriver

```python
from cv_pom.cv_pom_driver import CVPOMDriver


class MyCVPOMDriver(CVPOMDriver):
    def __init__(self, model_path: str | Path, your_driver, **kwargs) -> None:
        super().__init__(model_path, **kwargs)
        self._driver = your_driver  # Store your driver so that you can use it later

    def _get_screenshot(self) -> ndarray:
        """Add the code that takes a screenshot"""

    def _click_coordinates(self, x: int, y: int):
        """Add the code that clicks on the (x,y) coordinates"""

    def _send_keys(self, keys: str):
        """Add the code that send keys"""

    def _swipe_coordinates(self, coords: tuple = None, direction: str = None):
        """Add the code that swipes/scrolls on the coords -> (x,y) and direction (up/down/left/right)"""

    def _hover_coordinates(self, x: int, y: int):
        """Add the code that hovers on the (x,y) coordinates"""

    def _drag_drop(self, x: int, y: int, x_end: int, y_end: int, duration=0.1):
        """Add the code that drags and drops on the (x,y) -> (x_end,y_end) coordinates"""
```

Then use it for automation
```python
framework_specific_driver = ... # Driver object you create with your automation framework of choice
model_path = "./my-model.pt"
kwargs = {'ocr': {'paragraph': True}} # Optional
cv_pom_driver = MyCVPOMDriver(model_path, framework_specific_driver, **kwargs)

# Find element by label
element = cv_pom_driver.find_element({"label": "reply-main"})
# Click on it
element.click()
# Wait until invisible
element.wait_invisible()
# Methods are also chainable
cv_pom_driver.find_element({"text": "some text"}).click()
# Get all elements to process them manually
cv_pom_driver.find_elements(None)
# Swipe/Scroll by coordinates coords=(x, y, x_end, y_end)
cv_pom_driver.swipe(coords=(10, 10, 400, 400))
# Swipe/Scroll by element
cv_pom_driver.find_element({"label": "reply-main"}).swipe(el=cv_pom_driver.find_element({"label": "rally"}))
# Swipe/Scroll by direction "up", "down", "left" and "right"
cv_pom_driver.find_element({"label": "reply-main"}).swipe(direction="down")
```
For now, the kwargs in `MyCVPOMDriver` is only used for `ocr` and the values are any parameters that EasyOCR allows under `self._reader.readtext(**ocr_props_comb)` check [here](https://www.jaided.ai/easyocr/documentation/)


For more info about the query syntax, look into the documentation of `POM.get_elements()` method (`cv_sdk/cv_pom.py`).


## Drivers Already Implemented

### Python-TestUI Driver - Selenium & Appium

To use this driver you will have to install both `cv_pom` and `python-testui` [![PyPI - Version](https://img.shields.io/pypi/v/python-testui)](https://pypi.org/project/python-testui/)

```bash
pip install python-testui
```

Now you can initialise the driver:

```python
import pytest
from selenium.webdriver.chrome.options import Options
from testui.support.appium_driver import NewDriver, TestUIDriver
from cv_pom.frameworks import TestUICVPOMDriver
from cv_pom.cv_pom_driver import CVPOMDriver

@pytest.fixture(autouse=True)
def testui_driver():
    
    options = Options()
    options.add_argument("--force-device-scale-factor=1")
    options.page_load_strategy = 'eager'
    driver = NewDriver().set_selenium_driver(chrome_options=options)
    driver.navigate_to("https://jqueryui.com/draggable/")
        
    yield driver
    driver.quit()

@pytest.fixture(autouse=True)
def cv_pom_driver(testui_driver):
    driver = TestUICVPOMDriver("yolov8n.pt", testui_driver, **{'ocr': {'paragraph': False}})
    yield driver

class TestSuite:
    def test_testdevlab(self, testui_driver: TestUIDriver, cv_pom_driver: CVPOMDriver):
        cv_pom_driver.element(
            {"text": {"value": "me around", "contains": True, "case_sensitive": False}}
        ).drag_drop(delta=(300, 0))
```

### PyAutoGui Driver - Native Desktop App Automation

This driver allows you to control the computer that it runs by using OS level interactions. It is very useful to automate **Native Desktop Applications**

To use this driver you will have to install both `cv_pom` and `pyautogui` [![PyPI - Version](https://img.shields.io/pypi/v/pyautogui)](https://pypi.org/project/pyautogui/)

```bash
pip install pyautogui
```

Now you can initialise the driver:

```python
import pytest
from cv_pom.frameworks import DesktopCVPOMDriver
from cv_pom.cv_pom_driver import CVPOMDriver

@pytest.fixture(autouse=True)
def cv_pom_driver():
    driver = DesktopCVPOMDriver("yolov8n.pt", **{'ocr': {'paragraph': False, 'canvas_size': 1200}, "resize": 0.5})
    yield driver


class TestSuite:
    def test_test_unicaja(self, cv_pom_driver: CVPOMDriver):
        page = cv_pom_driver.get_page()
        page.element({"text": {"value": "Project", "contains": True}}).drag_drop(delta=(500, 0))
```

IMPORTANT NOTE: for MacOS you might need to use `"resize": 0.5` for the arguments in the Driver, as the resolution of the screen is double the size due to the retina screens.


## CVPOM usage

### Python API

The methods for every driver are meant to be able to automate any workflow in any given app. Those methods are described in the above sections.

Besides those, there are also some useful classes that allows you to interact/filter elements:


`get_page` method allows the user to parse all the visible screen and then do interactions with it, like clicking, sending keys, etc.
```python
page = cv_pom_driver.get_page()
page.element({"text": {"value": "Project", "contains": True}}).click()
```

if the element is not visible when the first call of `get_page` happens, then it will try to parse the elements again (you can specify the timeouts, defaults to 10s)

For debugging purposes, you can also retrieve all the elements and print them in terminal or represent them in an image:

```python
page = cv_pom_driver.get_page()
print(page._pom.to_json())

import cv2
cv2.imshow("annotated_image", page._pom.annotated_frame)
cv2.waitKey(1000)
```


        - select by exact label:                {"label": "my-label"}
        - select by label containing substring: {"label": {"value: "my-label", "contains": True}}
        - select by label not case sensitive:   {"label": {"value: "my-label", "case_sensitive": False}}
        - select by exact text:                 {"text": "my-text"}
        - select by exact label and text:       {"label": "my-label", "text": "my-text"}


See tests or `CVPOMDriver` implementation for examples of how to use the underlying CVPOM class.


### REST API Server

You can run a rest API server in order to use the framework remotely or to use it with other programming languages:

```bash
python server.py --model yolov8n.pt
```

### As CLI

You can also inspect the elements in images by using the `main.py` script
```bash
python main.py --model yolov8n.pt --media test/resources/yolo_test_1.png
```
