import cv2 as cv
import numpy as np
import os
import re
import serial
import time

from importlib import reload
from pathlib import Path
from cv_pom.cv_pom_driver import CVPOMDriver

from config.printer_config import dimensions, SERIAL_PORT, BAUD_RATE 
# dimensions have the values of the printer bed size in mm
# SERIAL_PORT is the connection of your device to the printer, and can be found with 'ls /dev/tty.*' terminal command
# BAUD_RATE is set to 115200

import config.device_params as device_params_module
# Mobile device dimensions 

class PrinterCVPOMDriver(CVPOMDriver):
    def __init__(self, model_path: str | Path, appium_driver, device: str, printer: str, orientation: str, **kwargs) -> None:
        super().__init__(model_path, **kwargs)
        self._driver = appium_driver 
        
        self._ser = None
        self._ser = self.get_connection()
        
        self._device, self._printer = self._load_configs(device, printer)
        self._orientation = orientation
        
        # Default position is the center of the base plate
        self._printer_center_x = self._printer["x"]/2
        self._printer_center_y = self._printer["y"]/2 
        
        if(self._device["center_x"] != 0.0):
            self._printer_center_x = self._device["center_x"]
            self._printer_center_y = self._device["center_y"] 
        
        
    def _load_configs(self, device: str, printer: str):
         # Get device configuration
        if device not in device_params_module.device_params:
            raise KeyError(f"Device '{device}' not found in device_params")
        device_config = device_params_module.device_params[device]

        # Get printer configuration
        if printer not in dimensions:
            raise KeyError(f"Printer '{printer}' not found in dimensions")
        printer_config = dimensions[printer]

        return device_config, printer_config
    
    def _screen_to_printer(self, x_screen: float, y_screen: float) -> tuple[int, int]:
        screen_width = self._device["width"]
        screen_height = self._device["height"]
        device_width = self._device["physical_width"]
        device_height = self._device["physical_height"]
        
        
        printer_x_center = self._printer_center_x
        printer_y_center = self._printer_center_y 

        # Adjust for orientation
        if self._orientation == "landscape":
            # Swap width/height and rotate coordinates
            screen_width, screen_height = screen_height, screen_width
            device_width, device_height = device_height, device_width

            # Convert portrait to landscape
            temp_x = x_screen
            x_screen = y_screen
            y_screen = screen_width - temp_x
        
        # Scale app position (in px) to real device physical position (mm)
        x_mm = (x_screen / screen_width) * device_width
        y_mm = (1 - (y_screen / screen_height)) * device_height  # Invert Y axis with (1 - ..)

        # Shift so center of the device = printer center
        x_mm_offset = x_mm - (device_width / 2)
        y_mm_offset = y_mm - (device_height / 2)

        # Translate device position relative to printer center
        printer_x = printer_x_center + x_mm_offset
        printer_y = printer_y_center + y_mm_offset

        return printer_x, printer_y

    def _get_screenshot(self) -> np.ndarray:
        png = self._driver.get_screenshot_as_png() # Get screenshot via appium

        # Convert PNG bytes to a numpy array
        arr = np.frombuffer(png, dtype=np.uint8)
        img = cv.imdecode(arr, cv.IMREAD_COLOR)
        
        # Save screenshot in screenshots folder
        save_path = os.path.join(os.path.dirname(__file__), "..", "screenshots")
        os.makedirs(save_path, exist_ok=True)
        cv.imwrite(os.path.join(save_path, "latest.png"), img)
        
        return img

    def _hover_coordinates(self, x: int, y: int):
        dx, dy = self._screen_to_printer(x, y)
        self.send_gcode(f"G1 X{dx:.2f} Y{dy:.2f} F3000") # Move to position
    
    def _click_coordinates(self, x: int, y: int, times=1, interval=0, button="PRIMARY"):
        dx, dy = self._screen_to_printer(x, y)
        self.send_gcode(f"G1 X{dx:.2f} Y{dy:.2f}") # Move to position
        self.send_gcode("G1 Z2 F6000") # Go down
        self.send_gcode("G1 Z10 F6000") # Go back up
        print("Tap!")

    def _swipe_coordinates(self, coords: tuple = None, direction: str = None, duration: float = 0.1):
        distance = 30 # How far to swipe
        self.send_gcode(f"G1 X{self._printer_center_x} Y{self._printer_center_y}") # Move to center position
        self.send_gcode("G1 Z2 F6000") # Go down
        
        # Swipe in the correct direction
        match direction:
            case "up":
                swipe = self._printer["y"]/2 + distance
                self.send_gcode(f"G1 Y{swipe} F6000")
            case "down":
                swipe = self._printer["y"]/2 - distance
                self.send_gcode(f"G1 Y{swipe} F6000")
            case "left":
                swipe = self._printer["x"]/2 - distance
                self.send_gcode(f"G1 X{swipe} F6000")
            case "right":
                swipe = self._printer["x"]/2 + distance
                self.send_gcode(f"G1 X{swipe} F6000")
            case _:
                print(f"Invalid direction: {direction}")
                return
            
        self.send_gcode("G1 Z10 F6000") # Go back up
        print(f"Swipe {direction}!")

    def _drag_drop(self, x: int, y: int, x_end: int, y_end: int, duration=0.1, button="PRIMARY"):
        dx, dy = self._screen_to_printer(x, y)
        ex, ey = self._screen_to_printer(x_end, y_end)
        self.send_gcode(f"G1 X{dx:.2f} Y{dy:.2f}") # Move to starting position
        self.send_gcode("G1 Z2") # Go down
        self.send_gcode(f"G1 X{ex:.2f} Y{ey:.2f}") # Move to the target position
        self.send_gcode("G1 Z10") # Go back up
        print(f"Drag and Drop!")
    
    # Not implemented
    def _send_keys(self, keys: str):
        raise NotImplementedError("Keyboard input functionality is not implemented.")
    
    
    ### --------------- Public methods ---------------
    
    # Get the current X,Y,Z position of the printer
    def get_position(self):
        ser = self.get_connection()
        self.send_gcode("M114")
        while True:
            line = ser.readline().decode(errors="ignore").strip()
            if line and "Count" in line:
                # M114 Output: X:230.00 Y:230.00 Z:12.60 E:0.00 Count X:18400 Y:18400 Z:5040
                match = re.search(r"X:([\d\.\-]+)\s+Y:([\d\.\-]+)\s+Z:([\d\.\-]+)", line)
                if match:
                    x = float(match.group(1))
                    y = float(match.group(2))
                    z = float(match.group(3))
                    return x, y, z
    
    # Use to send any gcode command to the printer     
    def send_gcode(self, cmd: str):
        ser = self.get_connection()

        # If cmd is a list or tuple, iterate through it
        if isinstance(cmd, (list, tuple)):
            for line in cmd:
                ser.write((line + "\r\n").encode())
                ser.flush()
                print(f">> {line}")
                time.sleep(0.05)
        
        # Treat it as a single string
        else:
            ser.write((cmd + "\r\n").encode())
            ser.flush()
            print(f">> {cmd}")
            time.sleep(0.05)
    
    # If manual calibration of the device position was done, call this method to update the center position of the device 
    def update_custom_position(self):
        try:
            reload(device_params_module) # Reload the file where the custom positions were added
            if "custom" in device_params_module.device_params:
                self._device = device_params_module.device_params["custom"]
                self._printer_center_x = self._device.get("center_x", self._printer_center_x)
                self._printer_center_y = self._device.get("center_y", self._printer_center_y)
                print(f"Custom calibration loaded: center=({self._printer_center_x:.2f}, {self._printer_center_y:.2f})")
            else:
                print("No 'custom' entry found in device_params.py.")
        except Exception as e:
            print(f"Failed to load custom calibration: {e}")
    
    # Connect to the printer via serial
    def get_connection(self):
        if self._ser is None:
            self._ser = serial.Serial(port= SERIAL_PORT, baudrate= BAUD_RATE)
            time.sleep(2)  # Wait for printer to be ready
            print("Serial connection established.")
        return self._ser
    
    # Close the existing connection
    def close_connection(self):
        if self._ser is not None:
            self._ser.close()
        print("Serial connection closed.")