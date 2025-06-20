# controllers.py

import time, curses, RPi.GPIO as GPIO
from simple_pid import PID

class HeaterController:
    def __init__(self, pins, setpt, thresh, pid_cfg):
        self.pins   = pins
        self.setpt  = setpt
        self.thresh = thresh
        self.pid    = PID(**pid_cfg)
        self.pid.setpoint     = setpt
        self.pid.output_limits = (0,1)

    def update(self, temp, now):
        duty = self.pid(temp)
        state = GPIO.HIGH if (now % 1.0) < duty else GPIO.LOW
        for p in self.pins:
            GPIO.output(p, state)

    def color(self, val):
        if val < self.setpt * self.thresh:
            return curses.color_pair(3)
        elif val < self.setpt:
            return curses.color_pair(9)
        else:
            return curses.color_pair(10)


class GasController:
    def __init__(self, pin, setpt, th, invert=False):
        self.pin     = pin
        self.setpt   = setpt
        self.invert  = invert

        for k in ('continuous', 'pulse', 'stop'):
            if k not in th:
                raise KeyError(f"GasController: thresholds missing key '{k}' for pin {pin}")

        self.th_cont = th['continuous']
        self.th_puls = th['pulse']
        self.th_off  = th['stop']

    def update(self, val, now):
        if not self.invert:
            cont  = val < self.setpt * self.th_cont
            pulse = val < self.setpt * self.th_puls
        else:
            cont  = val > self.setpt * self.th_cont
            pulse = val > self.setpt * self.th_puls

        if cont:
            GPIO.output(self.pin, GPIO.HIGH)
        elif pulse:
            st = GPIO.HIGH if (now % 1.0) < 0.5 else GPIO.LOW
            GPIO.output(self.pin, st)
        else:
            GPIO.output(self.pin, GPIO.LOW)

    def color(self, val):
        if not self.invert:
            if val < self.setpt * self.th_off:
                return curses.color_pair(2)
            elif val < self.setpt * self.th_cont:
                return curses.color_pair(7)
            else:
                return curses.color_pair(8)
        else:
            if val > self.setpt * self.th_off:
                return curses.color_pair(1)
            elif val > self.setpt * self.th_cont:
                return curses.color_pair(5)
            else:
                return curses.color_pair(6)
