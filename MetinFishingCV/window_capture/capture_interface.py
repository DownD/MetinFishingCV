# import protocol
from abc import ABC, abstractmethod
import numpy as np

class WindowCapture(ABC):
    @abstractmethod
    def get_screenshot(self) -> tuple[np.ndarray, int, int]:
        pass

    @abstractmethod
    def set_window_name(self) -> str:
        pass