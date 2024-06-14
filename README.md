# CV_POM

## Introduction

CV POM framework provides tools to detect elements in image content and interact with them.

### CV POM
CV POM converts any image into a page object model. This model lets you access the elements recognized in the image. Elements contain such properties as labels, coordinates and others. It's also possible to transform the elements into a JSON representation for easy integration with other tools.

### CV POM Driver
CV POM Driver is built on top of CV POM and provides easy integration with any automation framework (like Selenium or Appium). The user just needs to overwrite a couple of methods of the `CVPOMDriver` class and then use it as a driver to find elements and interact with them.

Since this approach doesn't require any APIs from the application to test, it is generic for every platform/app combination, allowing the user to automate for each platform with the same APIs. It also allows the automation of workflows based on the UI representation, which validates the stylings and placement of each of the elements, which is something that most UI automation frameworks lack.

## Install

```bash
pip install cv_pom
```

## CV_POM usage

### CVPOMDriver usage

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

### CVPOM usage
See tests or `CVPOMDriver` implementation for examples of how to use the underlying CVPOM class.

### As CLI

You can also inspect the elements in images by using the `main.py` script
```bash
python main.py --model test/resources/best_august.pt --media test/resources/yolo_test_1.png
```
