import serial
import struct
import logging
import threading
import time
import serial.tools.list_ports

SERIAL_ARDUINO_VID = 9025
DEFAULT_BAUD_RATE = 115200


class SerialHandler:
    """
    Class to communicate with an Arduino Leonardo using serial.
    It sends commands to the Arduino Leonardo by serial that will be interpreted by the Arduino Leonardo.
    This class is meant to be used with the Arduino Leonardo sketch in the Arduino folder, and send the data
    using a very simple custom custom protocol explained in more detail in the sketch.

    Read function not implemented yet.
    """

    def __init__(self, port: str = None, baudrate: int = DEFAULT_BAUD_RATE, log_serial: bool = False):
        """
        Initializes the SerialMouseHandler class
            If the port is not specified, it will try to find the first Arduino Leonardo
        by using the ARDUINO VID.


        Args:
            port (str): The port to connect to
            baudrate (int): The baudrate to use
            log_serial (bool, optional): Whether to log serial data. Defaults to False.
        """

        if port is None:
            # Attempt to find arduino port by checking connected device's VID
            ports = list(serial.tools.list_ports.comports())
            for p in ports:
                if p.vid == SERIAL_ARDUINO_VID:
                    port = p.device
                    break

            if port is None:
                raise RuntimeError("Could not find Arduino Leonardo port")

        self.__serial_object = serial.Serial(port, baudrate)
        self.__serial_object.flushInput()
        self.__serial_logger = logging.getLogger("SerialDeviceLogs")
        self.__serial_handler_logger = logging.getLogger("SerialHandler")
        self.__log_thread = threading.Thread(target=self.__listen_logs)

        if log_serial:
            logging.getLogger("SerialDeviceLogs").setLevel(logging.DEBUG)
            logging.getLogger("SerialHandler").setLevel(logging.DEBUG)

            # Create thread
            self.__log_thread.daemon = True
            # Start thread
            self.__log_thread.start()

        self.__serial_handler_logger.info(
            f"Connected to Arduino Leonardo on port {port} using baudrate {baudrate}")

    def __listen_logs(self):
        """
        Listens for logs from the serial port

        REMARKS: This function will change later when the read communication is implemented
        """
        while True:
            while self.__serial_object.in_waiting:
                data = self.__serial_object.readline()
                self.__serial_logger.debug(data.decode("utf-8").strip())
                time.sleep(0.05)

            time.sleep(0.4)

    def read(self):
        """
        Reads data from the serial port

        Returns:
            bytes: The data read from the serial port
        """
        raise NotImplementedError()

    def write(self, data : bytes):
        """
        Writes data to the serial port

        Args:
            data (bytes): The data to write to the serial port
        """
        packet_length = len(data)
        packet = struct.pack(f"<B{packet_length}s", packet_length, data)
        self.__serial_handler_logger.debug(
            f"Sending packet: {packet} with length {packet_length}")
        self.__serial_object.write(packet)
