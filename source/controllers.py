# controllers.py

import time, logging, curses, RPi.GPIO as GPIO
from simple_pid import PID

logger = logging.getLogger("incubator.controllers")

class HeaterController:
    def __init__(self, pins, setpt, thresh, pid_cfg):
        self.pins        = pins
        self.setpt       = setpt
        self.thresh      = thresh
        self.pid         = PID(**pid_cfg)
        self.pid.setpoint = setpt
        self.pid.output_limits = (0,1)

    def update(self, temp, now):
        duty  = self.pid(temp)  # 0..1
        state = GPIO.HIGH if (now % 1.0) < duty else GPIO.LOW
        for p in self.pins:
            GPIO.output(p, state)

    def color(self, val):
        if val < self.setpt * self.thresh:
            return curses.color_pair(3)   # WHITE
        elif val < self.setpt:
            return curses.color_pair(9)   # GREEN
        else:
            return curses.color_pair(10)  # RED

class GasController:
    def __init__(self, pin, setpt, thresholds, invert=False):
        """
        thresholds: dict with keys 'continuous', 'pulse', 'stop'
        invert=False for CO₂ (lower→on), True for O₂ (higher→on)
        """
        self.pin    = pin
        self.setpt  = setpt
        self.invert = invert

        # pull out your three thresholds
        for k in ('continuous','pulse','stop'):
            if k not in thresholds:
                raise KeyError(f"GasController: missing '{k}' threshold")
        self.th_cont = thresholds['continuous']
        self.th_puls = thresholds['pulse']
        self.th_stop = thresholds['stop']

    def is_continuous(self, val):
        """True if we are in the “full‐on” zone."""
        if self.invert:
            return val > self.setpt * self.th_cont
        else:   
            return val < self.setpt * self.th_cont

    def force_off(self):
        """Immediately close/stop this valve."""
        GPIO.output(self.pin, GPIO.LOW)

    def update(self, val, now):
        # full-on wins
        if self.is_continuous(val):
            GPIO.output(self.pin, GPIO.HIGH)
            return

        # otherwise decide pulse vs off
        if self.invert:
            pulse = val > self.setpt * self.th_puls
        else:
            pulse = val < self.setpt * self.th_puls

        if pulse: #80% duty cycle, 1 second pulses
            state = GPIO.HIGH if (now % 1.0) < 0.8 else GPIO.LOW
            GPIO.output(self.pin, state)
        else:
            GPIO.output(self.pin, GPIO.LOW)

    def color(self, val):
        # reuse same bands to pick display color
        if self.is_continuous(val):
            return curses.color_pair(6) if self.invert else curses.color_pair(8)
        if (val > self.setpt * self.th_stop) if self.invert else (val < self.setpt * self.th_stop):
            # in “stop” band
            return curses.color_pair(1) if self.invert else curses.color_pair(2)
        # else we’re in the pulse band
        return curses.color_pair(5) if self.invert else curses.color_pair(7)
