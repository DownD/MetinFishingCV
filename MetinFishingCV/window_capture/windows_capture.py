import win32gui
import dxcam
import numpy as np
from MetinFishingCV.window_capture.capture_interface import WindowCapture

class WindowsCapture(WindowCapture):
    """
    Class that allows to capture a window from the screen using dxcam module in windows.

    REMARKS: Currently only works on Windows with DPI at 100% and on the main screen.
    """

    def __init__(self):
        """
        Initialize the dxcam object to capture a specific window.
        """

        self.camera = dxcam.create(output_color="BGR")
        self.monitors = dxcam.get_monitors()
        self.hwnd = None

    def set_window_name(self, window_name: str):
        """
        Set the window name to capture.

        Args:
            window_name (str): window name to capture.

        Raises:
            RuntimeError: If the window is not found. 
        """

        self.hwnd = win32gui.FindWindow(None, window_name)
        if not self.hwnd:
            raise RuntimeError(f'Window not found: {window_name}')

    def get_screenshot(self) -> tuple[np.ndarray, int, int]:
        """
        Get a screenshot of the window.

        Returns:
            tuple[ndarray, int, int]: The image grab and it's position.
        """

        window_rect = win32gui.GetWindowRect(self.hwnd)

        start_x = min(self.monitors[0].width, max(0, window_rect[0]))
        start_y = min(self.monitors[0].height, max(0, window_rect[1]))
        end_x = min(self.monitors[0].width, max(0, window_rect[2]))
        end_y = min(self.monitors[0].height, max(0, window_rect[3]))

        if end_x == 0 or end_y == 0:
            return None

        return self.camera.grab(region=[start_x, start_y, end_x, end_y]), start_x, start_y

    def list_window_names(self):
        """
        List all the window names that can be captured.
        """
        def winEnumHandler(hwnd, ctx):
            if win32gui.IsWindowVisible(hwnd):
                print(hex(hwnd), win32gui.GetWindowText(hwnd))
        win32gui.EnumWindows(winEnumHandler, None)