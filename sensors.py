# sensors.py

import time, logging, serial

log = logging.getLogger("incubator.sensors")

class SerialGas:
    def __init__(self, port, cmd, scale, baud=9600, reopen_delay=2.0):
        self.port_name    = port
        self.cmd          = cmd.encode('ascii') if isinstance(cmd, str) else cmd
        self.scale        = scale
        self.baud         = baud
        self.reopen_delay = reopen_delay
        self._open_port()

    def _open_port(self):
        try:
            if hasattr(self, 'ser'):
                self.ser.close()
            self.ser = serial.Serial(self.port_name,
                                     self.baud,
                                     timeout=1,
                                     write_timeout=1)
            time.sleep(0.5)
            log.info(f"Opened gas sensor on {self.port_name} @ {self.baud} baud")
        except Exception:
            log.exception(f"Failed to open gas port {self.port_name}")
            raise

    def _read_once(self):
        self.ser.reset_input_buffer()
        self.ser.write(self.cmd + b"\r\n")
        line = self.ser.readline()
        if not line:
            raise RuntimeError("empty response")
        tok = line.decode('ascii', errors='ignore').strip().split()
        if len(tok) < 2 or not tok[1].isdigit():
            raise ValueError(f"unexpected token sequence: {tok!r}")
        raw = int(tok[1])
        return raw * self.scale

    def read(self):
        try:
            return self._read_once()
        except Exception:
            log.warning(f"{self.port_name}: read failed, reopening port…")
            try:
                time.sleep(self.reopen_delay)
                self._open_port()
                return self._read_once()
            except Exception:
                log.error(f"{self.port_name}: still failing after reopen")
                return 0.0


class SensorSupervisor:
    """
    Wrap any sensor class and if it fails N times in a row,
    re‐instantiate it once, then keep returning last good value.
    """
    def __init__(self, cls, max_failures=3, *args, **kwargs):
        self._factory     = (cls, args, kwargs)
        self.max_failures = max_failures
        self._reset()

    def _reset(self):
        cls, args, kwargs = self._factory
        self.sensor     = cls(*args, **kwargs)
        self.fail_count = 0
        self.last_value = 0.0
        log.info(f"{cls.__name__}Supervisor: created new instance")

    def read(self):
        try:
            v = self.sensor.read()
            if v == 0.0:
                raise RuntimeError("zero reading")
            self.fail_count = 0
            self.last_value = v
            return v
        except Exception as e:
            self.fail_count += 1
            log.warning(f"{self.sensor.__class__.__name__} read failed "
                        f"[{self.fail_count}/{self.max_failures}]: {e}")
            if self.fail_count >= self.max_failures:
                log.error("Too many failures, re-instantiating sensor…")
                try:
                    self._reset()
                except Exception:
                    log.exception("Re-instantiate also failed")
                self.fail_count = 0
            return self.last_value
