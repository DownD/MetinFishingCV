from Xlib import display, X
import numpy as np
from mss import mss
from typing import Optional
from MetinFishingCV.window_capture.capture_interface import WindowCapture

class LinuxCapture(WindowCapture):
    
    def __init__(self) -> None:

        # Window variables that will be set after the call to set_window_name
        self.__window_name :  Optional[str] = None
        self.__window_id : Optional[int]= None
        self.__wnd_resource : Optional[object]= None

        self.__root_window = display.Display().screen().root
        self.__disp = display.Display()
        self.__sct = mss()
        self.__sct_args = {'top': 0, 'left': 0, 'width': 1, 'height': 1}

    def __get_window_position(self) -> tuple[int, int, int, int]:    
        # get the geometry of the window
        geometry = self.__wnd_resource.get_geometry()
        coords = geometry.root.translate_coords(self.__window_id, 0, 0)

        # print the window position and dimensions
        return coords.x , coords.y,geometry.width, geometry.height

    def __get_window_id(self) -> int:
        win_list = self.__root_window.get_full_property(self.__disp.intern_atom('_NET_CLIENT_LIST'), 
                                   X.AnyPropertyType).value

        # iterate through the windows and look for the one with the matching name
        win_id = None
        for win_id in win_list:
            win_obj = self.__disp.create_resource_object('window', win_id)
            win_name = win_obj.get_full_property(self.__disp.intern_atom('_NET_WM_NAME'), 
                                                  X.AnyPropertyType).value
            if not win_name:
                continue
            
            if win_name.decode() == self.__window_name:
                return win_id
            
    def set_window_name(self, window_name: str) -> None:
        self.__window_name = window_name
        self.__window_id = self.__get_window_id()
        self.__wnd_resource = self.__disp.create_resource_object('window', self.__window_id)


    def get_screenshot(self) -> tuple[np.ndarray, int, int]:
        x,y, width, height = self.__get_window_position()
        self.__sct_args['top'] = y
        self.__sct_args['left'] = x
        self.__sct_args['width'] = width
        self.__sct_args['height'] = height

        img = self.__sct.grab(self.__sct_args)
        return np.array(img), x, y