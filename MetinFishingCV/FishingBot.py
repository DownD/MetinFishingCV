from typing import Callable
import argparse
import random
from time import sleep
import time
import logging
from MetinFishingCV.window_capture import GeneralCapture, WindowCapture
import cv2
from threading import Thread, Lock
from MetinFishingCV.InteractionHandler import SerialMouseHandler, InteractionHandlerInterface, DirectInputHandler
from MetinFishingCV.FishingDetection import FishingVision

_logger = logging.getLogger("FishingBot")


class FishingBot:
    """
    Main fishing bot class that takes care of the bot logic.
    - It uses FishingDetection to detect the fish and the game window.
    - It uses InteractionHandler to send mouse clicks to the game window by using an Arduino
      to bypass any client protection.
    - It uses dx_cam to capture the game window at extremely fast framerate.
    """

    class State:
        """
        State helper class to better manage the State system
        """

        def __init__(self, state: str, max_timeout_sec: float, action: Callable, on_time_out: Callable = lambda: None):
            """
            Creates a State object

            Args:
                state (str): State name
                max_timeout_sec (float): Maximum time in seconds before the state is considered as timed out
                action (Callable): Action to execute while in this state
                on_time_out (Callable, optional): Action to execute while after the state get's timed out. Defaults to lambda:None.
            """
            self.end_time = time.time() + max_timeout_sec
            self.time_out_delay = max_timeout_sec
            self.state = state
            self.action = action
            self.action_on_timeout = on_time_out

        def __eq__(self, __o: object) -> bool:
            """
            Compares the state name with the given object

            Args:
                __o (object): _description_

            Returns:
                bool: _description_
            """
            if isinstance(__o, FishingBot.State):
                return self.state == __o.state
            else:
                self.state == __o

        def __hash__(self) -> int:
            """
            Returns the hash of the state name

            Returns:
                int: returns the hash of the state name
            """
            return self.state.__hash__()

        def execute_action(self, *args, **kwargs):
            """
            Executes the action of this state
            """
            self.action(*args, **kwargs)

        def execute_on_timeout(self, *args, **kwargs):
            """
            Executes the action on timeout of this state
            """
            self.action_on_timeout(*args, **kwargs)

        def start(self):
            """
            Starts the state
            """
            self.end_time = time.time() + self.time_out_delay

        def is_time_up(self) -> bool:
            """
            Checks if the state is timed out

            Returns:
                bool: True if the state is timed out, False otherwise
            """

            return time.time() > self.end_time

    def __init__(self, wnd_capture: WindowCapture, resize_factor: float, interaction_handler: InteractionHandlerInterface, debug=False, fast=False):
        """
        Creates a new FishingBot object

        Args:
            wnd_capture (WindowCapture): An object that captures the game window
            resize_factor (float): Factor to resize the captured image
            interaction_handler (InteractionHandlerInterface): InteractionHandler to send mouse/keyboard events to the game window
            debug (bool, optional): If should be initialize in debug. Defaults to False.
            fast (bool, optional): If should run in fast mode (using synchronous method and no visualization). Defaults to False.
        """

        # Related to new thread if not in fast mode
        self.image_data: dict  # THIS IS A RESOURCE USED IN MULTIPLE THREADS
        self.data_lock = Lock()

        # Keeps track of the statistics
        self.__stats = {
            # Number of fish caught (this value is incremented if 3 clicks where sent in state_searching_fish)
            "fish_caught": 0,
            # Number of clicks sent to the game (clicks sent to the fish)
            "clicks_sent": 0,
        }
        self.__fish_striked = 0  # Number of times the fish was clicked in the current state

        # Dependencies
        self.__mouse_handler = interaction_handler
        self.__vision_processing = FishingVision(
            debug=debug, resize_factor=resize_factor)
        self.__wnd_capture = wnd_capture

        # Switch that determines if the bot is running
        self.__run_bot = True
        # Switch that determines if the bot is in fast mode
        self.__fast = fast

        # States of the bot
        self.__states = {
            "PULLING_ROD": FishingBot.State("PULLING_ROD", 4, self.state_pulling_rod, self.state_putting_bait),
            "SEARCHING_FISH": FishingBot.State("SEARCHING_FISH", 15, self.state_searching_fish, lambda: self.change_state("PULLING_ROD")),
            "WAIT_AFTER_CLICK": FishingBot.State("WAIT_AFTER_CLICK", 1, lambda *args, **kwargs: None, lambda: self.change_state("SEARCHING_FISH"))
        }
        # Current state of the bot
        self.__current_state: FishingBot.State = self.__states['PULLING_ROD']

    def change_state(self, state: str):
        """
        Changes the current state of the bot.

        Args:
            state (str): The new state, should be on of the keys of the states dict
        """
        _logger.debug(f"Changing state to {state}")

        if state == "PULLING_ROD":
            if self.__fish_striked >= 3:
                self.__stats["fish_caught"] += 1
                _logger.info(f"Fish caught: {str(self.__stats)}")
            self.__fish_striked = 0

        self.__current_state = self.__states[state]
        self.__current_state.start()

    def state_pulling_rod(self, game_on: bool, *args, **kwargs):
        """
        CallbackFunction.
        This state is called while the rod is being pulled.
        Args:
            game_on (bool): True if the fishing game is on and was detected
        """

        # If the fishing game was detected, change state to searching fish immediately
        if game_on:
            self.change_state("SEARCHING_FISH")
            _logger.debug(f"Game was detected, going back to searching")

    def state_searching_fish(self, x: int, y: int, w: int, h: int, fishable: bool, fish_detectable: bool, game_on: bool, *args, **kwargs):
        """
        CallbackFunction.
        This state is called while the bit is looking for a fish.
        Args:
            x (int): x coordinate of the fish
            y (int): y coordinate of the fish
            w (int): width of the fish box
            h (int): height of the fish box
            fishable (bool): True if the fish is in the circle
            fish_detectable (bool): True if the fish is in the fishing game
            game_on (bool): True if the game is on and was detected
        """

        # If the fishing game window is not detected change state to pulling rod
        if not game_on:
            self.change_state("PULLING_ROD")
            _logger.debug(f"Game was not detected waiting for rod")
            return

        # If fish was found inside the circle, send a click to the position
        if fish_detectable and fishable:
            _logger.debug(f"Sending click on x={x+w/2} y={y+h/2}")
            self.send_fish_click(x+w/2, y+h/2)
            self.change_state("WAIT_AFTER_CLICK")
        else:
            _logger.debug(
                f"Can't catch fish, fish_detectable={fish_detectable} fishable={fishable}")

    def state_putting_bait(self):
        """
        CallbackFunction.
        This state is called after the rod has been pulled.
        """
        self.send_put_bait()
        sleep(random.uniform(0.1, 0.2))
        self.send_start_fishing()
        self.change_state("SEARCHING_FISH")
        sleep(random.uniform(1.5, 3))

    def send_start_fishing(self):
        """
        Sends a click to the hotkey '<space>' to start fishing
        """
        _logger.info(f"Start Fishing")
        self.__mouse_handler.send_key_press(
            'space', delay_min_s=0.1, delay_max_s=0.3)

    def send_put_bait(self):
        """
        Sends a click to the hotkey '1' to put bait on the rod
        """
        _logger.info(f"Putting bait")
        self.__mouse_handler.send_key_press(
            '1', delay_min_s=0.1, delay_max_s=0.3)

    def send_fish_click(self, x: int, y: int):
        """
        Sends a click to the game window

        Args:
            x (str): x position of the fish
            y (str): y position of the fish
        """
        self.__mouse_handler.send_mouse_move(x, y)
        self.__fish_striked += 1
        self.__stats["clicks_sent"] += 1
        _logger.info(
            f"Mouse click since frame started: {(time.time()-self.__curr_time_frame)*1000}ms")
        self.__mouse_handler.send_mouse_left_click(
            delay_min_s=0.01, delay_max_s=0.05)

    def thread_run(self):
        """
        This is the main thread that runs the bot if not in fast mode.
        """
        while True:
            self.on_process()

    def on_process(self):
        """
        This function is called every frame if not in fast mode.
        If in fast mode is called directly after the detection is done.
        """
        if not self.__fast:
            self.data_lock.acquire()
            data = self.image_data.copy()
            self.data_lock.release()
        else:
            data = self.image_data

        if self.__current_state.is_time_up():
            _logger.info(
                f"Timeout has been reached for {self.__current_state.state}")
            self.__current_state.execute_on_timeout()
        else:
            self.__current_state.execute_action(**data)

    def run(self):
        """
        Main loop of the bot
        """
        self.image_data = {
            "x": 0,
            "y": 0,
            "w": 0,
            "h": 0,
            "fishable": False,
            "fish_detectable": False,
            "game_on": False
        }

        if not self.__fast:

            # Show the image capture window if not in fast method
            thread = Thread(target=self.thread_run)
            thread.daemon = True  # Also terminate secondary thread
            thread.start()

            window_name = "Vision"
            cv2.namedWindow(window_name)
            cv2.moveWindow(window_name, 0, 30)

        while 1:
            try:
                frame, start_x, start_y = self.__wnd_capture.get_screenshot()
            except Exception as e:
                print("Final stats:\n")
                print(self.__stats)
                return
            if frame is not None:

                # Run the vision detection algorithm
                self.__curr_time_frame = time.time()
                x, y, w, h, fishable, fish_detectable, game_on = self.__vision_processing.get_fishing_state(
                    frame)

                _logger.debug(
                    f"Detection frame processing time: {(time.time()-self.__curr_time_frame)*1000}ms")

                # If not in fast mode, acquire the lock to store the data
                if not self.__fast:
                    self.data_lock.acquire()

                # Store the data
                self.image_data = {
                    "x": x+start_x,
                    "y": y+start_y,
                    "w": w,
                    "h": h,
                    "fishable": fishable,
                    "fish_detectable": fish_detectable,
                    "game_on": game_on
                }

                # If in fast mode, call the on_process function and continue to next frame
                if self.__fast:
                    self.on_process()
                    continue

                # Release the data
                self.data_lock.release()

                # Setup the frame
                dbg_frame = self.__vision_processing.get_debug_frame()
                if dbg_frame is not None:
                    # Draw special debug frame if in debug mode
                    cv2.imshow(window_name, dbg_frame)
                else:
                    # Draw raw frame if not in debug mode with detected fish
                    if game_on:
                        cv2.rectangle(frame, (x, y), (x+w, y+h),
                                      (0, 0, 255), 2)

                    cv2.imshow(window_name, frame)

                # If the user presses 'esc' turn off/on the action
                if cv2.waitKey(1) == 27:
                    self.__run_bot = not self.__run_bot
                    _logger.info(f"Bot state changed to {self.__run_bot}")


def main():

    logging.basicConfig(
        level=logging.INFO, format="[%(asctime)s.%(msecs)03d][%(name)s][%(levelname)s] - %(message)s", datefmt="%H:%M:%S")

    # Parse args
    parser = argparse.ArgumentParser()
    parser.add_argument('--resize_factor', nargs='?',
                        default=0.5, const=0.5, type=float, help="Define the factor the image should be resized before processing")
    parser.add_argument('--debug', nargs='?',
                        default=False, const=True, type=bool, help="Display additional logs and extra information in window")
    parser.add_argument('--fast', nargs='?', default=False,
                        const=True, type=bool, help="Fast mode without debug window and single threaded")
    parser.add_argument('--use_arduino', nargs='?', default=False,
                        const=True, type=bool, help="Use the arduino to send the mouse clicks")
    parser.add_argument('window_name', help="The window name of the game")
    args = parser.parse_args()

    if args.debug:
        _logger.setLevel(logging.DEBUG)
    else:
        _logger.setLevel(logging.INFO)

    if args.use_arduino:
        mouse_keyboard_handler = SerialMouseHandler(log_serial=args.debug)
    else:
        mouse_keyboard_handler = DirectInputHandler()

    cap = GeneralCapture()
    cap.set_window_name(args.window_name)

    fishing = FishingBot(wnd_capture=cap, debug=args.debug, interaction_handler=mouse_keyboard_handler,
                         resize_factor=args.resize_factor, fast=args.fast)
    fishing.run()


if __name__ == '__main__':
    main()
