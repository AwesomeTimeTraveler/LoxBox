# controllers.py  (replace GasController only)
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
    def __init__(self, pin, setpt, thresholds, invert=False,
                 # new timing/anti-overshoot knobs:
                 pulse_on_s=0.10,        # length of a single CO₂ "micro-pulse"
                 settle_s=5.0,           # refractory: wait this long after any pulse
                 startup_soft_secs=120,  # during first N seconds after boot use longer settle / shorter ON
                 startup_pulse_on_s=0.06,
                 startup_settle_s=8.0,
                 # rate limit:
                 rise_suppression=0.20   # if dC/dt > 0.20 %/s, suppress pulses
                 ):
        """
        thresholds: dict with keys 'continuous', 'pulse', 'stop'
        invert=False for CO₂ (lower→on), True for O₂ (higher→on)
        """
        self.pin     = pin
        self.setpt   = setpt
        self.invert  = invert

        for k in ('continuous','pulse','stop'):
            if k not in thresholds:
                raise KeyError(f"GasController: missing '{k}' threshold")
        self.th_cont = thresholds['continuous']
        self.th_puls = thresholds['pulse']
        self.th_stop = thresholds['stop']

        # anti-overshoot parameters
        self.pulse_on_s         = float(pulse_on_s)
        self.settle_s           = float(settle_s)
        self.startup_soft_secs  = float(startup_soft_secs)
        self.startup_pulse_on_s = float(startup_pulse_on_s)
        self.startup_settle_s   = float(startup_settle_s)
        self.rise_suppression   = float(rise_suppression)

        # internal state
        self.last_pulse_end = 0.0   # time of last valve OFF
        self.last_val       = None  # last CO₂/O₂ measurement
        self.last_t         = None  # last timestamp
        self.last_state     = GPIO.LOW

        GPIO.output(self.pin, GPIO.LOW)

    def is_continuous(self, val):
        if self.invert:  # O₂ controller
            return val > self.setpt * self.th_cont
        else:            # CO₂ controller
            return val < self.setpt * self.th_cont

    def _in_pulse_band(self, val):
        if self.invert:
            return val > self.setpt * self.th_puls
        else:
            return val < self.setpt * self.th_puls

    def force_off(self):
        GPIO.output(self.pin, GPIO.LOW)
        self.last_state = GPIO.LOW

    def update(self, val, now):
        # 0) Continuous band wins (same as your current logic)
        if self.is_continuous(val):
            GPIO.output(self.pin, GPIO.HIGH)
            self.last_state = GPIO.HIGH
            return

        # 1) Decide if we’re even eligible to pulse
        in_pulse = self._in_pulse_band(val)
        if not in_pulse:
            self.force_off()
            return

        # 2) Compute rise rate dV/dt (simple derivative) for suppression
        dvdt = 0.0
        if self.last_val is not None and self.last_t is not None:
            dt = max(1e-3, now - self.last_t)
            dvdt = (val - self.last_val) / dt  # % per second
        self.last_val, self.last_t = val, now

        # If rising too fast, don't add more
        if (not self.invert) and dvdt > self.rise_suppression:
            # CO₂ rising quickly; hold off
            self.force_off()
            return
        if self.invert and dvdt < -self.rise_suppression:
            # For O₂ (invert=True), a large NEGATIVE dv/dt means O₂ is dropping fast (purge effective)
            self.force_off()
            return

        # 3) Enforce settle/refractory after any pulse
        # Use longer settle and shorter pulses during startup/boot
        in_startup = (now < self.startup_soft_secs)
        on_len   = self.startup_pulse_on_s if in_startup else self.pulse_on_s
        settle   = self.startup_settle_s   if in_startup else self.settle_s

        time_since_pulse = now - self.last_pulse_end
        if time_since_pulse < settle:
            # still settling; keep valve closed
            self.force_off()
            return

        # 4) Deliver exactly one micro-pulse, then enter settle again
        # We implement the micro-pulse by turning it on until (now - last_pulse_end) < on_len,
        # then turning it off and booking last_pulse_end = now.
        if self.last_state == GPIO.LOW and time_since_pulse >= settle:
            # start a new pulse
            GPIO.output(self.pin, GPIO.HIGH)
            self.last_state = GPIO.HIGH
            # record the moment we started the pulse using a latch
            self.pulse_started_at = now
            return

        # If valve is open, close it after on_len elapsed and enter settle
        if self.last_state == GPIO.HIGH:
            if (now - getattr(self, 'pulse_started_at', now)) >= on_len:
                GPIO.output(self.pin, GPIO.LOW)
                self.last_state = GPIO.LOW
                self.last_pulse_end = now
            # otherwise keep it ON until on_len expires
            return

        # default off
        self.force_off()

    def color(self, val):
        if self.is_continuous(val):
            return curses.color_pair(6) if self.invert else curses.color_pair(8)
        if (val > self.setpt * self.th_stop) if self.invert else (val < self.setpt * self.th_stop):
            return curses.color_pair(1) if self.invert else curses.color_pair(2)
        return curses.color_pair(5) if self.invert else curses.color_pair(7)
