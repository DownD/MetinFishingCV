import cv2
from typing import Tuple
from numpy import ndarray, array
import numpy as np
from MetinFishingCV.window_capture import GeneralCapture
from MetinFishingCV.cv_utils import get_image_template, detect_object_color, overlay_image
import logging
import time
import os

_logger = logging.getLogger("FishingVision")


class FishingVision():

    """
    Class responsible for detecting the fish game window, the fish position and the circle.
    """
    # GAME MATCH TEMPLATE PATH
    GAME_TEMPLATE_PATH = os.path.join("resources","template_fish_game_border.png")

    # Match template threshold
    GAME_THRESHOLD = 0.7

    # BORDER CROP
    BORDER_OFFSET = 10
    BORDER_OFFSET_TITLE = 28

    # FISH
    FISH_COLOR_LBOUND = array([73, 99, 116])
    FISH_COLOR_HBOUND = array([144, 154, 132])

    # GRAB_DETECTION
    GRAB_COLOR_LBOUND = array([118, 56, 141])
    GRAB_COLOR_HBOUND = array([255, 144, 255])
    GRAB_THRESHOLD_SUM = 40000  # Threshold for the number of pixels light up

    def __init__(self, lower_scale=1, higher_scale=1, num_templates_searches=1, debug=False, resize_factor=0.3):
        """
        Initialize the FishingVision class

        Args:
            lower_scale (int, optional): The lower scale/ratio of each screenshot to be used on get_image_template. Defaults to 1.
            higher_scale (int, optional): The higher scale/ratio of each screenshot to be used on get_image_template. Defaults to 1.
            num_templates_searches (int, optional): The number of templates searches to be done between lower_scale abd higher_scale. Defaults to 1.
            debug (bool, optional): If debug mode should be used. Defaults to False.
            resize_factor (float, optional): The resize factor that should be applied before the processing (Currently only used in matchTemplate). Defaults to 0.3.
        """
        # Match template related
        self.__lower_scale = lower_scale
        self.__higher_scale = higher_scale
        self.__num_templates_searches = num_templates_searches
        self.__resize_factor = resize_factor
        # Template to be matched
        self.__template_game: ndarray = cv2.imread(
            str(self.GAME_TEMPLATE_PATH))
        # Apply smoothing for better results
        self.__template_game = cv2.bilateralFilter(
            self.__template_game, 7, 85, 85)

        # Debug related
        self.__debug = debug
        self.__dbg_image: ndarray = None

    def __get_fish_pos(self, img_crop: ndarray) -> Tuple[int, int, int, int, bool, ndarray]:
        """
        Get the fish position and the circle position by using color range matching

        Args:
            img_crop (ndarray): The cropped fishing game image

        Returns:
            Tuple[int,int,int,int,bool,ndarray]: x,y,width,height,found,debug_mask
        """
        try:
            x, y, w, h, dbg_img = detect_object_color(
                img_crop, self.FISH_COLOR_LBOUND, self.FISH_COLOR_HBOUND, self.__debug)
        except ValueError as e:
            return 0, 0, 0, 0, False, img_crop
        return x, y, w, h, True, dbg_img

    def __get_circle_fishable_px_count(self, cropped: ndarray) -> Tuple[ndarray, float]:
        """
        Get the number of pixels that are light up in the fishing game, using color range matching, in order to find the circle

        Args:
            cropped (ndarray): The cropped fishing game image

        Returns:
            Tuple[ndarray,float]: The mask resulting of the search, the number of pixels that are light up
        """
        # Set color
        into_hsv = cv2.cvtColor(cropped, cv2.COLOR_BGR2HSV)

        # Get Range
        b_mask = cv2.inRange(
            into_hsv, self.GRAB_COLOR_LBOUND, self.GRAB_COLOR_HBOUND)

        sum_pixels = np.sum(b_mask)

        return b_mask, sum_pixels

    def get_game_template_crop(self, image: ndarray) -> Tuple[int, int, int, int, float, float]:
        """
        Get the fishing game position and correlation value by using matchTemplate

        Args:
            image (ndarray): Game image

        Returns:
            Tuple[int,int,int,int,float,float]: x,y,width,height,confidence,scale_result
        """
        x, y, width, height, corr, scale = get_image_template(image, self.__template_game,
                                                              high_scale=self.__higher_scale,
                                                              low_scale=self.__lower_scale,
                                                              num_searches=self.__num_templates_searches,
                                                              resize_factor=self.__resize_factor
                                                              )

        start_y = y + self.BORDER_OFFSET + self.BORDER_OFFSET_TITLE
        start_x = x + self.BORDER_OFFSET

        return start_x, start_y, width - self.BORDER_OFFSET*2, height - self.BORDER_OFFSET*2 - self.BORDER_OFFSET_TITLE, corr, scale

    def get_fishing_state(self, image: ndarray) -> Tuple[int, int, int, int, bool, bool, bool]:
        """
        Get the data from the frame.
        Searches for the fishing game, using matchTemplate, and then searches for the fish and the circle, using color range matching.

        Args:
            image (ndarray): The frame to be processed

        Returns:
            Tuple[int,int,int,int,bool,bool,bool]: x,y,width,height,found_circle,found_fish,found_game
        """
        blured_image = cv2.bilateralFilter(image, 7, 85, 85)
        x, y, width, height, corr, scale = self.get_game_template_crop(
            blured_image)

        img_cropped = blured_image[y:y+height, x:x+width]

        # Checks if the fish game is running
        if corr > self.GAME_THRESHOLD:
            _logger.debug(f"Window state found: corr={corr}")

            # Get the possibility of catch the fish
            circle_mask, fishable_confidence = self.__get_circle_fishable_px_count(
                img_cropped)
            is_fishable = True if fishable_confidence > self.GRAB_THRESHOLD_SUM else False
            _logger.debug(
                f"Fish catchable confidence_value={fishable_confidence} is_fishable={is_fishable}")

            # Get fish position
            x_fish, y_fish, w_fish, h_fish, detected_fish, dbg_fish_image = self.__get_fish_pos(
                img_cropped)
            _logger.debug(
                f"Fish at x:{x_fish} y:{y_fish} w:{w_fish} h:{h_fish} detection:{detected_fish}")

            # Save a debug image with the view of the algorithm
            if self.__debug:
                self.__dbg_image = cv2.blur(image, (8, 8))

                if is_fishable:
                    dbg_fish_image[circle_mask > 0] = (0, 155, 0)
                else:
                    dbg_fish_image[circle_mask > 0] = (0, 0, 155)

                self.__dbg_image = overlay_image(
                    self.__dbg_image, dbg_fish_image, x, y)

            return x_fish+x, y_fish+y, w_fish, h_fish, is_fishable, detected_fish, True

        else:
            if self.__debug:
                self.__dbg_image = cv2.blur(image, (8, 8))
                self.__dbg_image = overlay_image(
                    self.__dbg_image, img_cropped, x, y)

            _logger.debug(f"Could not find the game window, corr={corr}")

            return 0, 0, 0, 0, False, False, False

    def get_debug_frame(self) -> ndarray:
        """
        Get an image related to the last frame processed.
        Only available if debug was passed as True in the constructor.

        Returns:
            ndarray: A debug image with information about the last vision.
        """
        if self.__debug:
            return self.__dbg_image
        else:
            return None


__last_time = time.time()


def __show_preview(frame, fish_vision):
    """
    Function intended only for debug purposes.
    """
    global __last_time

    _logger.debug(f'Frame size shape: {frame.shape}')
    x, y, w, h, fishable, fish_detectable, game_on = fish_vision.get_fishing_state(
        frame)

    curr_time = time.time()
    delta_time = curr_time-__last_time

    print(f'FPS:{int(1/delta_time)}')

    dbg_frame = fish_vision.get_debug_frame()
    if dbg_frame is not None:
        cv2.imshow("Vision-dbg", dbg_frame)

    if game_on:
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)

    cv2.imshow("Vision", frame)

    __last_time = curr_time
    if cv2.waitKey(1) == 27:
        return False

    return True


def main():
    import argparse
    logging.basicConfig(
        level=logging.INFO, format="[%(asctime)s][%(levelname)s] - %(message)s", datefmt="%H:%M:%S")
    _logger.setLevel(logging.DEBUG)

    # Parse args
    parser = argparse.ArgumentParser()
    parser.add_argument('--video', type=str)
    parser.add_argument('--window', type=str)
    parser.add_argument('--debug', nargs='?',
                        default=False, const=True, type=bool)
    args = parser.parse_args()

    fish_vision = FishingVision(debug=args.debug)

    if args.video:
        # Open video

        _logger.info(f"Running tests in video {args.video}")
        cap = cv2.VideoCapture(args.video)
        if not cap.isOpened():
            raise Exception(f"Fail to open video: {args.video}")
        while 1:
            ret, frame = cap.read()

            if not ret:
                break

            if not __show_preview(frame, fish_vision):
                break

    elif args.window:
        _logger.info(f"Running tests in window {args.window}")

        wnd_capture = GeneralCapture()
        wnd_capture.set_window_name(args.window)

        while 1:
            frame, x, y = wnd_capture.get_screenshot()
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            if frame is not None:
                if not __show_preview(frame, fish_vision):
                    break

    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
