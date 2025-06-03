#!/usr/bin/env python3
import time, sys, curses, traceback
import serial
import RPi.GPIO as GPIO
from w1thermsensor import W1ThermSensor
import board, busio
from adafruit_ht16k33 import segments

# ─── CONFIGURATION & TUNING ─────────────────────────────────────────────────────
CO2_PORT      = "/dev/ttyUSB0"     # USB-UART for CO₂ sensor
O2_PORT       = "/dev/serial0"     # Pi-UART for O₂ sensor
BAUD_RATE     = 9600
READ_INTERVAL = 0.5
LOGFILE       = "metrics_regulation_log.txt"

# Setpoints & thresholds
temp_set    = 37.0;  temp_thresh = 0.98
o2_set      =  2.0;  o2_thresh  = 0.85
co2_set     =  5.0;  co2_thresh = 0.85

# Sensor max ranges for bar scaling
O2_MAX      = 25.0    # O₂ sensor max %
CO2_MAX     = 20.0    # CO₂ sensor max %
TEMP_MAX    = 50.0    # Temperature max °C

# ─── GPIO pins (BCM numbering) ──────────────────────────────────────────────────
O2_PIN     = 20   # O₂ solenoid relay
CO2_PIN    = 21   # CO₂ solenoid relay

# Six heater relays (example BCM pins; adjust to your actual wiring):
HEATER_PINS = [5, 6, 13, 19, 26, 27]

# ─── SERIAL SETUP ───────────────────────────────────────────────────────────────
def open_serial(port_name, label):
    """Utility to open a serial port or exit with an error."""
    try:
        ser = serial.Serial(port_name, BAUD_RATE, timeout=1)
        time.sleep(2)
        return ser
    except Exception as e:
        print(f"[FATAL] Cannot open {label} port {port_name}: {e}", file=sys.stderr)
        sys.exit(1)

o2_ser  = open_serial(O2_PORT,  "O₂")
co2_ser = open_serial(CO2_PORT, "CO₂")

# ─── TEMPERATURE SENSORS ───────────────────────────────────────────────────────
try:
    temp_sensors = W1ThermSensor.get_available_sensors()
    if not temp_sensors:
        print("[WARNING] No DS18B20 sensors found.", file=sys.stderr)
except Exception as e:
    print(f"[ERROR] Temp sensor init failed: {e}", file=sys.stderr)
    temp_sensors = []

def read_temperature():
    """Read average of all DS18B20 probes, or return 0.0 if anything goes wrong."""
    try:
        vals = []
        for s in temp_sensors:
            try:
                vals.append(s.get_temperature())
            except Exception:
                pass
        return sum(vals) / len(vals) if vals else 0.0
    except Exception as e:
        print(f"[ERROR] read_temperature exception: {e}", file=sys.stderr)
        return 0.0

# ─── GPIO RELAY SETUP ─────────────────────────────────────────────────────────
GPIO.setmode(GPIO.BCM)
# Gas pumps
for p in (O2_PIN, CO2_PIN):
    GPIO.setup(p, GPIO.OUT)
    GPIO.output(p, GPIO.LOW)
# Heaters (all six)
for hp in HEATER_PINS:
    GPIO.setup(hp, GPIO.OUT)
    GPIO.output(hp, GPIO.LOW)

# ─── I2C & 7-SEGMENT SETUP ─────────────────────────────────────────────────────
i2c = busio.I2C(board.SCL, board.SDA)
try:
    disp_o2   = segments.Seg7x4(i2c, 0x70); disp_o2.brightness = 5
except Exception as e:
    print(f"[ERROR] Failed to init O₂ display @0x70: {e}", file=sys.stderr)
    disp_o2 = None

try:
    disp_co2  = segments.Seg7x4(i2c, 0x71); disp_co2.brightness = 5
except Exception as e:
    print(f"[ERROR] Failed to init CO₂ display @0x71: {e}", file=sys.stderr)
    disp_co2 = None

try:
    disp_temp = segments.Seg7x4(i2c, 0x72); disp_temp.brightness = 5
except Exception as e:
    print(f"[ERROR] Failed to init Temp display @0x72: {e}", file=sys.stderr)
    disp_temp = None

# ─── LOGGING ───────────────────────────────────────────────────────────────────
try:
    log = open(LOGFILE, "a")
except Exception as e:
    print(f"[ERROR] Cannot open log file: {e}", file=sys.stderr)
    log = None

def log_metrics(ts, t, o, c):
    """Write a single line to the logfile (or stderr if logging fails)."""
    if not log:
        return
    try:
        log.write(f"{ts}\tT:{t:.2f}\tO2:{o:.2f}\tCO2:{c:.2f}\n")
        log.flush()
    except Exception as e:
        print(f"[ERROR] Logging failed: {e}", file=sys.stderr)

# ─── SENSOR READS ─────────────────────────────────────────────────────────────
def read_o2():
    """Poll the O₂ UART; return 0.0 on any error."""
    try:
        o2_ser.reset_input_buffer()
        o2_ser.write(b"%\r\n")
        time.sleep(0.1)
        tok = o2_ser.readline().decode("ascii", errors="replace").split()
        if len(tok) >= 2 and tok[1].isdigit():
            return float(tok[1]) * 0.001
        return 0.0
    except Exception as e:
        print(f"[ERROR] read_o2 exception: {e}", file=sys.stderr)
        return 0.0

def read_co2():
    """Poll the CO₂ UART; return 0.0 on any error."""
    try:
        co2_ser.reset_input_buffer()
        co2_ser.write(b"Z\r\n")
        time.sleep(0.1)
        tok = co2_ser.readline().decode("ascii", errors="replace").split()
        if len(tok) >= 2 and tok[1].isdigit():
            return int(tok[1]) * 10 / 10000.0
        return 0.0
    except Exception as e:
        print(f"[ERROR] read_co2 exception: {e}", file=sys.stderr)
        return 0.0

# ─── BAR COLOR UTILITY ─────────────────────────────────────────────────────────
def bar_color(val, setpt, thresh):
    """Return a curses color pair based on thresholds:
       < thresh*setpt → green; between → yellow; ≥ setpt → magenta."""
    if val < setpt * thresh:
        return curses.color_pair(1)   # GREEN
    elif val < setpt:
        return curses.color_pair(5)   # YELLOW
    else:
        return curses.color_pair(6)   # MAGENTA

# ─── MAIN UI LOOP ──────────────────────────────────────────────────────────────
def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN,   -1)
    curses.init_pair(2, curses.COLOR_BLUE,    -1)
    curses.init_pair(3, curses.COLOR_RED,     -1)
    curses.init_pair(4, curses.COLOR_WHITE,   -1)
    curses.init_pair(5, curses.COLOR_YELLOW,  -1)
    curses.init_pair(6, curses.COLOR_MAGENTA, -1)

    max_y, max_x = stdscr.getmaxyx()
    bar_w = max_x - 20
    start = time.time()

    # Precompute gas tick labels (0%, 25%, 50%, 75%, 100%)
    ticks = [0, O2_MAX / 4, O2_MAX / 2, 3 * O2_MAX / 4, O2_MAX]
    tick_labels = [f"{x:.0f}%" for x in ticks]
    # Precompute temp tick labels (0, 12, 25, 37, 50)
    temp_ticks  = [0, TEMP_MAX / 4, TEMP_MAX / 2, 3 * TEMP_MAX / 4, TEMP_MAX]
    temp_labels = [f"{x:.0f}" for x in temp_ticks]

    while True:
        try:
            # 1) Read sensors
            t = read_temperature()
            o = read_o2()
            c = read_co2()

            # 2) Log metrics
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            log_metrics(ts, t, o, c)

            # 3) Regulation logic
            now = time.time() - start

            # ─── 3a) Heaters (all six) ───────────────────────────────────────────
            if t < temp_thresh * temp_set:
                # below threshold → all heaters ON
                for hpin in HEATER_PINS:
                    GPIO.output(hpin, GPIO.HIGH)
            elif t < temp_set:
                # stepping: 0.5s ON, 0.5s OFF
                cycle = now % 1.0
                state = GPIO.HIGH if cycle < 0.5 else GPIO.LOW
                for hpin in HEATER_PINS:
                    GPIO.output(hpin, state)
            else:
                # above setpoint → all OFF
                for hpin in HEATER_PINS:
                    GPIO.output(hpin, GPIO.LOW)

            # ─── 3b) O₂ solenoid ────────────────────────────────────────────────
            if o < o2_thresh * o2_set:
                GPIO.output(O2_PIN, GPIO.HIGH)
            elif o < o2_set:
                cycle = now % 1.0
                GPIO.output(O2_PIN, GPIO.HIGH if cycle < 0.5 else GPIO.LOW)
            else:
                GPIO.output(O2_PIN, GPIO.LOW)

            # ─── 3c) CO₂ solenoid ───────────────────────────────────────────────
            if c < co2_thresh * co2_set:
                GPIO.output(CO2_PIN, GPIO.HIGH)
            elif c < co2_set:
                cycle = now % 1.0
                GPIO.output(CO2_PIN, GPIO.HIGH if cycle < 0.5 else GPIO.LOW)
            else:
                GPIO.output(CO2_PIN, GPIO.LOW)

            # 4) Draw the text and bars
            stdscr.erase()

            # ─── GAS bars (single line at row 1) ───────────────────────────────────
            # O₂ label + bar at (1,1) and (1,12)
            stdscr.addstr(1, 1,  f"O₂: {o:5.2f}%", curses.color_pair(4))
            w_o = min(int(o / O2_MAX * bar_w), bar_w)
            stdscr.addnstr(1, 12, "█" * w_o, bar_w, bar_color(o, o2_set, o2_thresh))
            # O₂ axis ticks on row 2
            for idx, _ in enumerate(ticks):
                xpos = 12 + int(idx * (bar_w / 4))
                stdscr.addstr(2, xpos, tick_labels[idx], curses.color_pair(4))

            # CO₂ label + bar (to the right of O₂ bar)
            offset = 12 + bar_w + 5
            stdscr.addstr(1, offset, f"CO₂: {c:5.2f}%", curses.color_pair(4))
            w_c = min(int(c / CO2_MAX * bar_w), bar_w)
            stdscr.addnstr(1,
                           offset + 7,
                           "█" * w_c,
                           bar_w,
                           bar_color(c, co2_set, co2_thresh))
            # CO₂ axis ticks on row 2
            for idx, _ in enumerate(ticks):
                xpos = offset + 7 + int(idx * (bar_w / 4))
                stdscr.addstr(2, xpos, tick_labels[idx], curses.color_pair(4))

            # ─── Temperature bar (row 4) ─────────────────────────────────────────
            stdscr.addstr(4, 1, f"Temp: {t:5.2f}°C", curses.color_pair(4))
            w_t = min(int(t / TEMP_MAX * bar_w), bar_w)
            stdscr.addnstr(4, 12, "█" * w_t, bar_w, bar_color(t, temp_set, temp_thresh))
            # Temperature axis ticks on row 5
            for idx, _ in enumerate(temp_ticks):
                xpos = 12 + int(idx * (bar_w / 4))
                stdscr.addstr(5, xpos, temp_labels[idx], curses.color_pair(4))

            # ─── 7-segment displays ──────────────────────────────────────────────
            if disp_o2:
                disp_o2.print(f"{o:05.2f}")
            if disp_co2:
                disp_co2.print(f"{c:05.2f}")
            if disp_temp:
                disp_temp.print(f"{t:05.2f}")

            stdscr.addstr(max_y - 2, 1, "Press 'q' to quit.", curses.color_pair(4))
            stdscr.refresh()

            # check for quit
            if stdscr.getch() == ord("q"):
                break

            time.sleep(READ_INTERVAL)

        except Exception:
            # If anything goes wrong, terminate curses, print traceback, and exit the loop
            curses.endwin()
            print("[FATAL] Exception in main loop:", file=sys.stderr)
            traceback.print_exc()
            break

if __name__ == "__main__":
    while True:
        try:
            curses.wrapper(main)
            # If main() exits normally (e.g. user pressed 'q'), break the outer loop
            break
        except Exception:
            # Some unexpected error during startup; ensure all relays off, print traceback,
            # then wait 5 seconds and try again.
            for pin in (O2_PIN, CO2_PIN) + tuple(HEATER_PINS):
                GPIO.output(pin, GPIO.LOW)
            print("[WARNING] Unhandled exception—will restart in 5 seconds.", file=sys.stderr)
            traceback.print_exc()
            time.sleep(5)

    # Final cleanup on exit
    for pin in (O2_PIN, CO2_PIN) + tuple(HEATER_PINS):
        GPIO.output(pin, GPIO.LOW)
    if log:
        log.close()
    o2_ser.close()
    co2_ser.close()
    sys.exit(0)
