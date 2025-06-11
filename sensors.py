# sensors.py

import time
import serial
import logging
from w1thermsensor import W1ThermSensor

logger = logging.getLogger("incubator.sensors")

class OneWireTemps:
    def __init__(self):
        try:
            self.sensors = W1ThermSensor.get_available_sensors() or []
        except Exception:
            logger.exception("Failed to initialize 1-Wire sensors")
            self.sensors = []

    def read(self):
        try:
            vals = [s.get_temperature() for s in self.sensors]
            return sum(vals)/len(vals) if vals else 0.0
        except Exception:
            logger.exception("Error reading temperature")
            return 0.0

class SerialGas:
    def __init__(self, port, cmd, scale, baud):
        self.scale = scale
        self.cmd = cmd.encode('ascii')
        try:
            self.ser = serial.Serial(port, baud, timeout=1)
            time.sleep(2)
        except Exception:
            logger.exception(f"Failed to open serial port {port}")
            raise

    def read(self):
        try:
            self.ser.reset_input_buffer()
            self.ser.write(self.cmd + b"\r\n")
            time.sleep(0.1)
            raw = self.ser.readline().decode('ascii', errors='replace').split()
            if len(raw) >= 2 and raw[1].isdigit():
                return float(raw[1]) * self.scale
            return 0.0
        except Exception:
            logger.exception(f"Error reading sensor with cmd {self.cmd!r}")
            return 0.0
