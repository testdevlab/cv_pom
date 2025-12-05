import cv2 as cv
import numpy as np
import math
import os
import re
import serial
import pygame
import time
import config.device_params as device_params_module
# Mobile device dimensions example:
#   device_params = {
#        "default": {
#            'width': 1080,
#            'height': 2640,
#           'physical_width': 38.0,
#           'physical_height': 102.0,
#           'center_x': 0.0,
#           'center_y': 0.0
#        }
#   }

from cv_pom.cv_pom_driver import CVPOMDriver
from importlib import reload
from pathlib import Path
from config.printer_config import dimensions, SERIAL_PORT, BAUD_RATE 
# SERIAL_PORT is the connection of your device to the printer, and can be found with 'ls /dev/tty.*' terminal command
# BAUD_RATE is set to 115200
# dimensions have the values of the printer bed size in mm
#   Example:
#   dimensions = {
#       "default":{
#           "x": 460, # In mm
#           "y": 460 
#       },
#   }


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

    def _hover_coordinates(self, x: int, y: int, wait_idle: bool = True):
        dx, dy = self._screen_to_printer(x, y)
        self.send_gcode(f"G1 X{dx:.2f} Y{dy:.2f} F3000") # Move to position
        if wait_idle:
            self.wait_until_idle()
    
    def _click_coordinates(self, x: int, y: int, times=1, interval=0, button="PRIMARY", wait_idle: bool = True):
        dx, dy = self._screen_to_printer(x, y)
        self.send_gcode(f"G1 X{dx:.2f} Y{dy:.2f}") # Move to position
        self.send_gcode("G1 Z0 F6000") # Go down
        self.send_gcode("G1 Z10 F6000") # Go back up
        print("Tap!")
        if wait_idle:
            self.wait_until_idle()

    def _swipe_coordinates(self, coords: tuple = None, direction: str = None, duration: float = 0.1, wait_idle: bool = True):
        distance = 30 # How far to swipe
        self.send_gcode(f"G1 X{self._printer_center_x} Y{self._printer_center_y}") # Move to center position
        self.send_gcode("G1 Z2 F6000") # Go down
        
        # Swipe in the correct direction
        if direction == "up":
            swipe = self._printer["y"] / 2 + distance
            self.send_gcode(f"G1 Y{swipe} F6000")
        elif direction == "down":
            swipe = self._printer["y"] / 2 - distance
            self.send_gcode(f"G1 Y{swipe} F6000")
        elif direction == "left":
            swipe = self._printer["x"] / 2 - distance
            self.send_gcode(f"G1 X{swipe} F6000")
        elif direction == "right":
            swipe = self._printer["x"] / 2 + distance
            self.send_gcode(f"G1 X{swipe} F6000")
        else:
            print(f"Invalid direction: {direction}")
            return
            
        self.send_gcode("G1 Z10 F6000") # Go back up
        print(f"Swipe {direction}!")
        
        if wait_idle:
            self.wait_until_idle()

    def _drag_drop(self, x: int, y: int, x_end: int, y_end: int, duration=0.1, button="PRIMARY", wait_idle: bool = True):
        dx, dy = self._screen_to_printer(x, y)
        ex, ey = self._screen_to_printer(x_end, y_end)
        self.send_gcode(f"G1 X{dx:.2f} Y{dy:.2f}") # Move to starting position
        self.send_gcode("G1 Z2") # Go down
        self.send_gcode(f"G1 X{ex:.2f} Y{ey:.2f}") # Move to the target position
        self.send_gcode("G1 Z10") # Go back up
        print("Drag and Drop!")
        if wait_idle:
            self.wait_until_idle()
    
    # Not implemented
    def _send_keys(self, keys: str):
        raise NotImplementedError("Keyboard input functionality is not implemented.")
    
    
    ### ------------------------------------------- Public methods -------------------------------------------
    
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
        
    def update_appium_driver(self, appium_driver):
        self._driver = appium_driver
        
    # Call to make the program wait until the printer has completed all commands
    def wait_until_idle(self, timeout_s: float = 60.0) -> bool:

        ser = self._ser

        # Remove any old data serial data
        old_timeout = ser.timeout
        ser.timeout = 0.1
        while True:
            data = ser.readline()
            if not data:
                break

        # Wait until all moves are done
        self.send_gcode("M400")

        deadline = time.time() + timeout_s
        ser.timeout = 0.5

        while time.time() < deadline:
            line = ser.readline().decode(errors="ignore").strip().lower()
            if not line:
                continue
            if line.startswith("busy"):
                continue
            if line == "ok":
                # Final OK after M400 means motion queue is empty
                ser.timeout = old_timeout
                # Returns a bool if more complex logic is needed during implementation
                return True

        # Timeout
        ser.timeout = old_timeout
        
        # Returns a bool if more complex logic is needed during implementation
        return False
        
        
  # ------------------------------------------- MANUAL CALIBRATION -------------------------------------------
    
    
    def manual_calibration(self):
        self._init_pygame()
        self.send_gcode("G1 Z10")  # lift head a bit

        # Reset saved positions at the start of calibration
        open("custom_position.txt", "w").close()
        clock = pygame.time.Clock()
        last_position = None

        corner_labels = ["Top Left", "Top Right", "Bottom Right", "Bottom Left"]
        coords = {} 
        idx = 0
        print(f"Select {corner_labels[idx]} corner, then left-click.")

        running = True
        while running:
            clock.tick(60)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.MOUSEMOTION:
                    x, y = event.pos
                    if (last_position is None) or (x, y) != last_position:
                        last_position = (x, y)
                        window_height = self._printer_center_y * 2
                        x, y = event.pos
                        y = window_height - y  # Inverts Y-axis when translating pygame window to printer. Remove this to undo the inversion
                        self._mouse_to_gcode(x, y)

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # tap down/up
                    self.send_gcode("G1 Z5 F3000")
                    self.send_gcode("G1 Z10 F3000")

                    x, y, _ = self.get_position()
                    print(f"[{corner_labels[idx]}] Current position: X={x:.2f}, Y={y:.2f}")

                    choice = input(f"Save this coordinate for {corner_labels[idx]}? (y/n): ").strip().lower()
                    if choice in ("y", "yes"):
                        label_key = corner_labels[idx].lower()
                        coords[label_key] = (x, y)
                        print("Coordinate saved.")

                        idx += 1
                        if idx >= 4:
                            print("All four corners saved. Exiting manual calibration.")
                            
                            # Ask for device name, default to "custom"
                            device_name = input('Device name to save (default "custom"): ').strip()
                            if not device_name:
                                device_name = "custom"

                            print(f"Saving calibration as '{device_name}'...")
                            self._add_custom_device_to_params(coords=coords, device_name=device_name)
                            print("Exiting manual calibration.")
                            
                            running = False
                        else:
                            print(f"Select {corner_labels[idx]} corner, then left-click.")
                    else:
                        print("Coordinate not saved. Try again for the same corner.")
    
    def _init_pygame(self, title: str = "Manual Control"):
        width = self._printer_center_x*2
        height = self._printer_center_y*2
        pygame.init()
        screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption(title)
        clock = pygame.time.Clock()
        return screen, clock

    def _get_mouse_position(self):
        return pygame.mouse.get_pos()


    def _mouse_to_gcode(self, x: int, y: int):
        
        # Creating new attributes to avoid sending every movement to the printer, only the last
        if not hasattr(self, "_last_move_time"):
            self._last_move_time = 0.0
            self._last_move_pos = None

        debounce_s = 0.15  # How many seconds to wait between sending last command to printer
        now = time.monotonic()

        # If not enough time passed since last method call, skip this one 
        if now - self._last_move_time < debounce_s:
            self._last_move_pos = (x, y)
            return

        # If we had a pending position from previous rapid moves, use that instead
        if self._last_move_pos is not None:
            x, y = self._last_move_pos
            self._last_move_pos = None

        self._last_move_time = now

        gcode = f"G1 X{x} Y{y} F10000"
        self.send_gcode(gcode)

    def _add_custom_device_to_params(self, coords: dict, device_name: str = "custom", params_path="config/device_params.py"):
        
        required = ["top left", "top right", "bottom right", "bottom left"]
        if any(label not in coords for label in required):
            raise ValueError(
                "Expected coordinates for Top Left, Top Right, Bottom Right, Bottom Left"
            )

        tl, tr, br, bl = (
            coords["top left"],
            coords["top right"],
            coords["bottom right"],
            coords["bottom left"],
        )

        # Compute dimensions
        width = math.dist(tl, tr)
        height = math.dist(tl, bl)

        # Compute physical center
        cx = (tl[0] + tr[0] + bl[0] + br[0]) / 4.0
        cy = (tl[1] + tr[1] + bl[1] + br[1]) / 4.0

        
        size = self._driver.get_window_size()
        screen_width = size["width"]
        screen_height = size["height"]

        entry = f"""
        '{device_name}': {{
            'width': {screen_width},
            'height': {screen_height},
            'physical_width': {width:.2f},
            'physical_height': {height:.2f},
            'center_x': {cx:.2f},
            'center_y': {cy:.2f}
        }},
        """

        # Update or append to device_params.py
        if not os.path.exists(params_path):
            with open(params_path, "w", encoding="utf-8") as f:
                f.write("device_params = {" + entry + "\n}\n")
            print(f"Created {params_path} and added '{device_name}' entry.")
            return

        with open(params_path, "r+", encoding="utf-8") as f:
            content = f.read()
            
            pattern = rf"'{re.escape(device_name)}':\s*\{{[^}}]+\}},"
            if f"'{device_name}':" in content:
                print(f"Updating existing '{device_name}' entry...")
                content = re.sub(pattern, entry.strip(), content)
            else:
                # Append before closing
                content = re.sub(r"\}\s*$", entry + "\n}", content)
                
            f.seek(0)
            f.write(content)
            f.truncate()

        print(f"Device '{device_name}' has been added/updated with width={width:.2f} mm, height={height:.2f} mm, center=({cx:.2f}, {cy:.2f})")