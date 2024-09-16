import time

from pathlib import Path
from cv_pom.cv_pom_driver import CVPOMDriver
import subprocess as sp
import cv2 as cv

from numpy import ndarray


class AdbCVPOMDriver(CVPOMDriver):
    def __init__(self, model_path: Path | str, url: str = None, udid: str = None) -> None:
        super().__init__(model_path)
        self.__udid = ""
        if udid is not None:
            self.__udid = f"-s {udid} "
        if url is not None:
            sp.run(f"adb {self.__udid}shell am start -a android.intent.action.VIEW -d {url}", shell=True)

    def _click_coordinates(self, x: int, y: int, times=1, interval=0, button="PRIMARY"):
        for _ in range(times):
            sp.run(f"adb {self.__udid}shell input tap {x} {y}", shell=True)
            time.sleep(interval)

    def _get_screenshot(self) -> ndarray:
        sp.run(f"adb {self.__udid}exec-out screencap -p > screen.png", shell=True)
        return cv.imread("screen.png")

    def _send_keys(self, keys: str):
        sp.run(f"adb {self.__udid}shell input text \"{keys}\"", shell=True)

    def _drag_drop(self, x: int, y: int, x_end: int, y_end: int, duration=0.1, button="PRIMARY"):
        sp.run(f"adb {self.__udid}shell input touchscreen swipe {x} {y} {x_end} {y_end}", shell=True)

    def _hover_coordinates(self, x: int, y: int):
        print("doesn't exist for ADB driver")

    def _swipe_coordinates(self, coords: tuple = None, direction: str = None, duration=None):
        # duration var doesn't have an effect in this driver

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

        sp.run(f"adb {self.__udid}shell input touchscreen swipe {x} {y} {x_end} {y_end}", shell=True)
