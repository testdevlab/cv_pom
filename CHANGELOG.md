# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0]
### Changed
- Reworked CV POM API

## [0.2.0]
### Changed
- Now you can add properties to OCR in convert_to_cvpom(source, ocr_props=None)
- This properties can be added to the CVPOMDriver in  the new kwargs:
```
kwargs = {'ocr': {'paragraph': True}} # Optional
MyCVPOMDriver(model_path, framework_specific_driver, **kwargs)
```

For now is only used for `ocr` and the values are any parameters that EasyOCR allows under `self._reader.readtext(**ocr_props_comb)` check [here](https://www.jaided.ai/easyocr/documentation/)

## [0.2.1]
### Changed
* adding pyautogui Driver (DesktopCVPOMDriver) to deal with OS native actions in https://github.com/testdevlab/cv_pom/pull/10
* adding offset to the coordinates for interactions in https://github.com/testdevlab/cv_pom/pull/12
* add double click and different click configurations in https://github.com/testdevlab/cv_pom/pull/13
* adding hover function in https://github.com/testdevlab/cv_pom/pull/14
* drag and drop methods in https://github.com/testdevlab/cv_pom/pull/15

## [0.2.2]
### Changed
* adding adb driver to control Android devices without Appium in https://github.com/testdevlab/cv_pom/pull/18
* adding querying in https://github.com/testdevlab/cv_pom/pull/21
* Feature: long press in https://github.com/testdevlab/cv_pom/pull/22