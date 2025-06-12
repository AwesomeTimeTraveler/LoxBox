# controllers.py

import time
import logging
import curses
import RPi.GPIO as GPIO
from simple_pid import PID

logger = logging.getLogger("incubator.controllers")

class HeaterController:
    def __init__(self, pins, setpoint, threshold, pid_cfg):
        """
        pins      – list of BCM pins for heater relays
        setpoint  – target temperature (°C)
        threshold – fraction below setpoint to hold heaters ON continuously
        pid_cfg   – dict with keys Kp, Ki, Kd, output_limits for PID
        """
        self.pins   = pins
        self.setpt  = setpoint
        self.thresh = threshold
        self.pid    = PID(**pid_cfg)
        self.pid.setpoint = setpoint

    def update(self, temp, now):
        """
        temp – current temperature
        now  – elapsed seconds since start
        """
        duty  = self.pid(temp)  # 0..1
        state = GPIO.HIGH if (now % 1) < duty else GPIO.LOW
        for p in self.pins:
            GPIO.output(p, state)

    def color(self, val):
        """Return curses color_pair for a given temperature"""
        if val < self.setpt * self.thresh:
            return curses.color_pair(3)   # WHITE
        elif val < self.setpt:
            return curses.color_pair(9)   # GREEN_BOLD
        else:
            return curses.color_pair(10)  # RED_BOLD

class GasController:
    def __init__(self, pin, setpoint, gas_thresholds, invert=False):
        """
        pin        – BCM pin for solenoid relay
        setpoint   – target gas concentration
        thresholds – dict with:
                      continuous: factor for continuous mode
                      pulse:      factor for stepping/pulse mode
                      off:        factor for OFF mode (reverse side of pulse)
        invert     – if True, comparisons invert (for O₂ displacement by N₂)
        """
        self.pin        = pin
        self.setpt      = setpoint
        self.thresh_c   = gas_thresholds['continuous']
        self.thresh_p   = gas_thresholds['pulse']
        self.thresh_off = gas_thresholds['off']
        self.invert     = invert

    def update(self, val, now):
        """
        val – current gas concentration
        now – elapsed seconds since start
        """
        if not self.invert:
            # CO₂: continuous if val < setpt * thresh_c
            cont  = val < self.setpt * self.thresh_c
            pulse = val < self.setpt * self.thresh_p
        else:
            # O₂: continuous if val > setpt * thresh_c
            cont  = val > self.setpt * self.thresh_c
            pulse = val > self.setpt * self.thresh_p

        if cont:
            GPIO.output(self.pin, GPIO.HIGH)
        elif pulse:
            state = GPIO.HIGH if (now % 1) < 0.5 else GPIO.LOW
            GPIO.output(self.pin, state)
        else:
            GPIO.output(self.pin, GPIO.LOW)

    def color(self, val):
        """Return curses color_pair for a given gas concentration"""
        if not self.invert:
            # CO₂: under setpt*off → CYAN; under setpt → BLUE; over → RED
            if val < self.setpt * self.thresh_off:
                return curses.color_pair(2)   # CYAN
            elif val < self.setpt:
                return curses.color_pair(7)   # BLUE
            else:
                return curses.color_pair(8)   # RED
        else:
            # O₂: over setpt*off → MAGENTA; over setpt → YELLOW; under → GREEN
            if val > self.setpt * self.thresh_off:
                return curses.color_pair(6)   # MAGENTA
            elif val > self.setpt:
                return curses.color_pair(5)   # YELLOW
            else:
                return curses.color_pair(1)   # GREEN
