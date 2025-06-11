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
        duty = self.pid(temp)  # fraction 0..1
        state = GPIO.HIGH if (now % 1) < duty else GPIO.LOW
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
    def __init__(self, pin, setpoint, threshold, invert=False):
        self.pin     = pin
        self.setpt   = setpoint
        self.thresh  = threshold
        self.invert  = invert

    def update(self, val, now):
        # continuous vs pulse thresholds
        if not self.invert:
            cont = val < self.setpt * (1 - 0.25)
            pulse = val < self.setpt * (1 - 0.10)
        else:
            cont = val > self.setpt * (1 + 0.25)
            pulse = val > self.setpt * (1 + 0.10)

        if cont:
            GPIO.output(self.pin, GPIO.HIGH)
        elif pulse:
            state = GPIO.HIGH if (now % 1) < 0.5 else GPIO.LOW
            GPIO.output(self.pin, state)
        else:
            GPIO.output(self.pin, GPIO.LOW)

    def color(self, val):
        if not self.invert:
            if val < self.setpt * self.thresh:
                return curses.color_pair(2)   # CYAN
            elif val < self.setpt:
                return curses.color_pair(7)   # BLUE
            else:
                return curses.color_pair(8)   # RED
        else:
            if val > self.setpt * self.thresh:
                return curses.color_pair(6)   # MAGENTA
            elif val > self.setpt:
                return curses.color_pair(5)   # YELLOW
            else:
                return curses.color_pair(1)   # GREEN
