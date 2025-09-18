# sensors.py

import time, logging, serial
from w1thermsensor import W1ThermSensor

log = logging.getLogger("incubator.sensors")

class OneWireTemps:
    def __init__(self):
        self.sensors = W1ThermSensor.get_available_sensors()
    def read(self):
        vs = []
        for s in self.sensors:
            try:
                vs.append(s.get_temperature())
            except: pass
        return sum(vs)/len(vs) if vs else 0.0

class SerialGas:
    def __init__(self, port, cmd, scale, baud=9600, reopen_delay=2.0):
        self.port_name    = port
        self.cmd           = cmd if isinstance(cmd,bytes) else cmd.encode('ascii')
        self.scale         = scale
        self.baud          = baud
        self.reopen_delay  = reopen_delay
        self._open_port()

    def _open_port(self):
        try:
            if hasattr(self, "ser"):
                self.ser.close()
            self.ser = serial.Serial(self.port_name, self.baud, timeout=1)
            time.sleep(0.5)
            log.info(f"Opened {self.port_name}@{self.baud}")
        except Exception:
            log.exception(f"Could not open {self.port_name}")
            raise

    def _read_once(self):
        self.ser.reset_input_buffer()
        self.ser.write(self.cmd)
        line = self.ser.readline()
        if not line:
            raise RuntimeError("empty response")
        tok = line.decode("ascii","ignore").strip().split()
        if len(tok)<2 or not tok[1].isdigit():
            raise ValueError(f"bad tokens {tok}")
        return int(tok[1]) * self.scale

    def read(self):
        try:
            return self._read_once()
        except Exception:
            log.warning(f"{self.port_name} read failed; reopening…")
            try:
                time.sleep(self.reopen_delay)
                self._open_port()
                return self._read_once()
            except Exception:
                log.error(f"{self.port_name} still failing")
                return 0.0

class SensorSupervisor:
    def __init__(self, cls, max_failures=3, *args, **kwargs):
        self.cls          = cls
        self.args         = args
        self.kwargs       = kwargs
        self.max_failures = max_failures
        self._reset()

    def _reset(self):
        self.sensor     = self.cls(*self.args, **self.kwargs)
        self.fail_count = 0
        self.last_value = 0.0
        log.info(f"{self.cls.__name__}Supervisor reset")

    def read(self):
        try:
            v = self.sensor.read()
            if v == 0.0:
                raise RuntimeError("zero")
            self.last_value = v
            self.fail_count  = 0
            return v
        except Exception as e:
            self.fail_count += 1
            log.warning(f"read failed [{self.fail_count}/{self.max_failures}]: {e}")
            if self.fail_count >= self.max_failures:
                log.error("max failures reached, resetting sensor")
                try:
                    self._reset()
                except:
                    log.exception("reset failed")
                self.fail_count = 0
            return self.last_value
