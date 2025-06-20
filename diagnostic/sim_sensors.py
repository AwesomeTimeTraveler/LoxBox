# sim_sensors.py

import itertools
import time

class SimOneWireTemps:
    def __init__(self, profile=None):
        # profile is a list of (timestamp_offset, temperature)
        # e.g. [(0,20), (10,25), (20,37)]
        self.profile = profile or [(0, 20.0), (5, 30.0), (10, 37.0)]
        self.start = time.time()
        self._iter = iter(self.profile)

    def read(self):
        now = time.time() - self.start
        # find the last entry in profile with offset <= now
        temp = self.profile[0][1]
        for offset, t in self.profile:
            if offset <= now:
                temp = t
            else:
                break
        return temp

class SimGas:
    def __init__(self, profile=None):
        self.profile = profile or [(0,20.0), (15,15.0), (30,2.0)]
        self.start = time.time()

    def read(self):
        now = time.time() - self.start
        val = self.profile[0][1]
        for offset, v in self.profile:
            if offset <= now:
                val = v
            else:
                break
        return val

class SimSupervisor:
    """Wraps a sim‐sensor so it matches SensorSupervisor interface."""
    def __init__(self, sim_cls, *args, **kwargs):
        self.sensor = sim_cls(*args, **kwargs)
    def read(self):
        return self.sensor.read()
