from typing import Tuple
from numpy import ndarray
import numpy as np
import cv2
from typing import Tuple


# https://pyimagesearch.com/2015/01/26/multi-scale-template-matching-using-python-opencv/
def get_image_template(img: ndarray, template: ndarray, low_scale=1.0, high_scale=1.0, num_searches=1, resize_factor=1) -> Tuple[int, int, int, int, float, float]:
    """
    Returns the location where the template has the best match alongside the respective correlation.
    This function will resize the image 'num_searches' times between 'low_scale' and 'high_scale' and returns the best template match. 

    Args:
        img (ndarray): The full image to be cropped.
        template (ndarray): The template image to be searched on img.
        low_scale (float, optional): The lower scale/ratio that the image should be subject to in order to try to match the template. Defaults to 0.2.
        high_scale (float, optional): The higher scale/ratio that the image should be subject to in order to try to match the template. Defaults to 1.4.
        num_searches (int, optional): The number of scale changes should be made. Defaults to 10.
        resize_factor (float, optional): The factor value (0-1) to downsampling the images
    Returns:
        Tuple[int,int,int,int,float,float]: (x, y, width, height, correlation, scale)Tupple containing the cropped image location and the correlation value.
    """
    # Size of original template
    (height, width) = template.shape[:2]

    # loop over the scales of the image
    template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Resize images if needed
    if resize_factor > 1:
        raise ValueError(
            "Only down-scalling is available, thus the resize value needs to be less then 1")

    elif resize_factor < 1:
        gray = cv2.resize(gray,
                          (int(gray.shape[1]*resize_factor),
                           int(gray.shape[0]*resize_factor)),
                          interpolation=cv2.INTER_AREA)

        template = cv2.resize(template,
                              (int(template.shape[1]*resize_factor),
                               int(template.shape[0]*resize_factor)),
                              interpolation=cv2.INTER_AREA)

    (tH, tW) = template.shape[:2]
    found = None
    for scale in np.linspace(low_scale, high_scale, num_searches)[::-1]:
        # resize the image according to the scale, and keep track
        # of the ratio of the resizing
        resized = cv2.resize(gray,
                             (int(gray.shape[1]*scale),
                              int(gray.shape[0]*scale)),
                             interpolation=cv2.INTER_AREA)
        r = 1/scale

        # if the resized image is smaller than the template, then break
        # from the loop
        if resized.shape[0] < tH or resized.shape[1] < tW:
            break

        result = cv2.matchTemplate(resized, template, cv2.TM_CCOEFF_NORMED)
        #print(f"Time MatchTemplate {(time.time()-start_time)*1000} ms")
        (_, maxVal, _, maxLoc) = cv2.minMaxLoc(result)
        # if we have found a new maximum correlation value, then update
        # the bookkeeping variable
        if found is None or maxVal > found[0]:
            found = (maxVal, maxLoc, r, scale)

    # unpack the bookkeeping variable and compute the (x, y) coordinates
    # of the bounding box based on the resized ratio
    (corr, maxLoc, r, scale) = found
    (startX, startY) = (int(maxLoc[0] * r), int(maxLoc[1] * r))
    (width, height) = (int(width * r), int(height * r))

    # Resize coordinates if needed
    if resize_factor < 1:
        inv_ratio = 1/resize_factor
        (startX, startY) = int(startX*inv_ratio), int(startY*inv_ratio)

    return startX, startY, width, height, corr, scale


def detect_object_color(img: ndarray, color_lbound: Tuple[int, int, int], color_hbound: Tuple[int, int, int], debug=False) -> Tuple[int, int, int, int, ndarray]:
    """
    Returns the bounding box of the bigger object found given the respective color bounds.
    It will also return an image, if debug is true, that represents what the algorithm sees.

    Args:
        img (ndarray): The image to search.
        color_lbound (List[int, int, int]): A color lower bound in format HSV where each value ranges from 0 to 255.
        color_hbound (List[int, int, int]): A color high bound in format HSV where each value ranges from 0 to 255.
        debug (bool, optional): If debug is true the last value returned will be an image with debug information. Defaults to False.

    Returns:
        Tuple[int,int,int,int,ndarray]: (x, y, width, height, debug_image) If debug is false, the last argument will always be None
    """
    into_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    # creating the mask using inRange() function
    # this will produce an image where the color of the objects
    # falling in the range will turn white and rest will be black

    b_mask = cv2.inRange(into_hsv, color_lbound, color_hbound)

    # Get countours
    contours, heirarchy = cv2.findContours(
        b_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if len(contours) == 0:
        raise ValueError("No objects found")

    # Get largest contour by area
    largest_cont = sorted(contours, key=cv2.contourArea, reverse=True)[0]

    # Get a bounding rect
    x, y, w, h = cv2.boundingRect(largest_cont)

    if debug:

        # Get the original image with mask
        res = cv2.bitwise_and(img, img, mask=b_mask)

        # Draw contours
        cv2.drawContours(res, contours, -1, (0, 255, 0), 3)

        # Draw the rectangle on the larger object
        cv2.rectangle(res, (x, y), (x+w, y+h), (0, 0, 255), 5)

        return x, y, w, h, res

    else:

        return x, y, w, h, None


def overlay_image(back_image: ndarray, front_image: ndarray, x_offset: int, y_offset: int) -> ndarray:
    """
    Edit the `back_image` and place the `front_image` on top of it at the specified offset.

    Args:
        back_image (ndarray): The image to be in the back.
        front_image (ndarray): The image to be in the front.
        x_offset (int): The x offset where to start pasting the front_image. 
        y_offset (int): The y offset where to start pasting the front_image.

    Returns:
        ndarray: the back_image edited.
    """
    back_image[y_offset:y_offset+front_image.shape[0],
               x_offset:x_offset+front_image.shape[1]] = front_image

    return back_image
