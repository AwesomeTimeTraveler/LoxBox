# controllers.py

import time, logging, curses
import RPi.GPIO as GPIO
from simple_pid import PID

logger = logging.getLogger("incubator.controllers")

class HeaterController:
    def __init__(self, pins, setpoint, threshold, pid_cfg):
        self.pins   = pins
        self.setpt  = setpoint
        self.thresh = threshold
        self.pid    = PID(**pid_cfg)
        self.pid.setpoint = setpoint

    def update(self, temp, now):
        duty  = max(0.0, min(1.0, self.pid(temp)))  # clamp to [0,1]
        state = GPIO.HIGH if (now % 1.0) < duty else GPIO.LOW
        for p in self.pins:
            GPIO.output(p, state)

    def color(self, val):
        if val < self.setpt * self.thresh:
            return curses.color_pair(3)   # WHITE
        elif val < self.setpt:
            return curses.color_pair(9)   # GREEN_BOLD
        else:
            return curses.color_pair(10)  # RED_BOLD


class GasController:
    def __init__(self, pin, setpoint, thresholds, invert=False):
        """
        thresholds: dict with keys continuous, pulse, off
        invert=False for CO₂, True for O₂
        """
        self.pin      = pin
        self.setpt    = setpoint
        self.th_cont  = thresholds['continuous']
        self.th_pulse = thresholds['pulse']
        self.th_off   = thresholds['off']
        self.invert   = invert

    def update(self, val, now):
        if self.invert:
            # O₂ displacement with N₂
            if val > self.setpt * self.th_cont:
                GPIO.output(self.pin, GPIO.HIGH)   # continuous purge
            elif val > self.setpt * self.th_pulse:
                state = GPIO.HIGH if (now % 1.0) < 0.5 else GPIO.LOW
                GPIO.output(self.pin, state)       # pulsed
            else:
                GPIO.output(self.pin, GPIO.LOW)    # off
        else:
            # CO₂ injection
            if val < self.setpt * self.th_cont:
                GPIO.output(self.pin, GPIO.HIGH)   # continuous injection
            elif val < self.setpt * self.th_pulse:
                state = GPIO.HIGH if (now % 1.0) < 0.5 else GPIO.LOW
                GPIO.output(self.pin, state)       # pulsed
            else:
                GPIO.output(self.pin, GPIO.LOW)    # off

    def color(self, val):
        if self.invert:
            if val > self.setpt * self.th_cont:
                return curses.color_pair(6)   # MAGENTA (continuous)
            elif val > self.setpt * self.th_pulse:
                return curses.color_pair(5)   # YELLOW  (pulse)
            else:
                return curses.color_pair(1)   # GREEN   (off)
        else:
            if val < self.setpt * self.th_cont:
                return curses.color_pair(2)   # CYAN    (continuous)
            elif val < self.setpt * self.th_pulse:
                return curses.color_pair(7)   # BLUE    (pulse)
            else:
                return curses.color_pair(8)   # RED     (off)
