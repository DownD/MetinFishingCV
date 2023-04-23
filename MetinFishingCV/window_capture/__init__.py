import os
from MetinFishingCV.window_capture.capture_interface import WindowCapture
if os.name == 'nt':
    from MetinFishingCV.window_capture.windows_capture import WindowsCapture as GeneralCapture
elif os.name == 'posix':
    from MetinFishingCV.window_capture.linux_capture import LinuxCapture as GeneralCapture
else:
    raise Exception("Unsupported OS")