import logging
import time
import random
from MetinFishingCV.SerialHandler import SerialHandler
import struct
import win32api
import pydirectinput

class InteractionHandlerInterface:
    """
    Interface that should be implemented by every class want's to define a new way
    of interacting with keyboard or mouse.
    """

    def __sleep_random_delay(self, delay_min_s: float, delay_max_s: float):
        """
        Sleeps for a random amount of time between delay_min_s and delay_max_s

        Args:
            delay_min_s (float): Minimum delay in milliseconds
            delay_max_s (float): Maximum delay in milliseconds
        """
        rnd = random.uniform(delay_min_s, delay_max_s)
        time.sleep(rnd)

    def send_key_press(self, key: str, delay_min_s: float, delay_max_s: float):
        """
        Sends a key press event

        Args:
            key (str): Key to press
            delay_min_ms (float): Minimum delay in milliseconds
            delay_max_ms (float): Maximum delay in milliseconds
        """
        self.send_key_down(key)
        self.__sleep_random_delay(delay_min_s, delay_max_s)
        self.send_key_up(key)

    def send_mouse_left_click(self, delay_min_s: float, delay_max_s: float):
        """
        Sends a mouse click event

        Args:
            delay_min_ms (float): Minimum delay in milliseconds
            delay_max_ms (float): Maximum delay in milliseconds
        """
        self.send_mouse_left_down()
        self.__sleep_random_delay(delay_min_s, delay_max_s)
        self.send_mouse_left_down()

    def send_mouse_move(self, x: int, y: int):
        raise NotImplementedError

    def send_mouse_left_down(self):
        raise NotImplementedError

    def send_mouse_left_up(self):
        raise NotImplementedError

    def send_key_down(self, key: str):
        raise NotImplementedError

    def send_key_up(self, key: str):
        raise NotImplementedError


class SerialMouseHandler(InteractionHandlerInterface):
    """
    Class that handles interaction with the Arduino Leonardo using a custom simple protcol
    defined in the SerialHandler class.
    For keyboard keystrokes will use the pyDirectInput library. This can be changed later
    by configuring the arduino to also send keyboard events.
    """

    COMMAND_LDOWN = 0
    COMMAND_LUP = 1
    COMMAND_MOUSEMOVE = 2

    def __init__(self, *args, **kwargs):
        """
        Initializes the SerialMouseHandler class
        """

        self.serial_handler = SerialHandler(*args, **kwargs)
        self.__logger = logging.getLogger("SerialMouseHandler")
        self.__logger.info("SerialMouseHandler Initialized")

    def send_relative_mouse_movement(self, x: int, y: int):
        """
        Sends a relative mouse movement command to the serial port
        Args:
            x (int): x relative movement
            y (int): y relative movement
        """
        self.serial_handler.write(struct.pack(
            '<Bhh', self.COMMAND_MOUSEMOVE, int(x), int(y)))
        self.__logger.debug(
            f"Sent relative mouse movement command to ({int(x)},{int(y)})")

    def send_mouse_move(self, x: int, y: int):
        """
        Sends an absolute mouse movement command to the serial port

        Args:
            x (int): x destination position
            y (int): y destination position
        """
        x_curr, y_curr = win32api.GetCursorPos()
        self.__logger.debug(
            f"Sent absolute mouse movement command to ({x},{y})")
        self.send_relative_mouse_movement(x-x_curr, y-y_curr)

    def send_mouse_left_down(self):
        """
        Sends a left mouse down command to the serial port
        """
        self.serial_handler.write(struct.pack('<B', self.COMMAND_LDOWN))

    def send_mouse_left_up(self):
        """
        Sends a left mouse up command to the serial port
        """
        self.serial_handler.write(struct.pack('<B', self.COMMAND_LUP))

    def send_key_down(self, key: str):
        """
        Sends a key down command

        Args:
            key (str): Key to press
        """
        pydirectinput.keyDown(key)

    def send_key_up(self, key: str):
        """
        Sends a key up command

        Args:
            key (str): Key to release
        """
        pydirectinput.keyUp(key)


class DirectInputHandler(InteractionHandlerInterface):
    """
    Class that handles interaction with the keyboard and mouse using pyDirectInput.
    """

    def send_mouse_move(self, x: int, y: int):
        """
        Sends an absolute mouse movement command to the serial port

        Args:
            x (int): x destination position
            y (int): y destination position
        """
        pydirectinput.moveTo(x, y)

    def send_mouse_left_down(self):
        """
        Sends a left mouse down command to the serial port
        """
        pydirectinput.mouseDown()

    def send_mouse_left_up(self):
        """
        Sends a left mouse up command to the serial port
        """
        pydirectinput.mouseUp()

    def send_key_down(self, key: str):
        """
        Sends a key down command

        Args:
            key (str): Key to press
        """
        pydirectinput.keyDown(key)

    def send_key_up(self, key: str):
        """
        Sends a key up command

        Args:
            key (str): Key to release
        """
        pydirectinput.keyUp(key)
