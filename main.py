#!/usr/bin/env python3
import os, sys, signal, time, curses
import yaml, logging, traceback
from logging.handlers import RotatingFileHandler
import RPi.GPIO as GPIO
import busio, board

from sensors import OneWireTemps, SerialGas, SensorSupervisor
from controllers import HeaterController, GasController
from display import DisplaySupervisor
from ui_curses import curses_main

# ─── 1) Load configuration
with open("/home/brennan/incubator/config.yaml") as f:
    cfg = yaml.safe_load(f)

# ─── 2) Setup rotating logger
handler = RotatingFileHandler(cfg['log_file'], maxBytes=1_000_000, backupCount=5)
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
logger = logging.getLogger("incubator")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# ─── 3) GPIO setup & ensure everything off
GPIO.setmode(GPIO.BCM)
all_pins = [cfg['gpio']['o2_pin'], cfg['gpio']['co2_pin']] + cfg['gpio']['heaters']
for p in all_pins:
    GPIO.setup(p, GPIO.OUT)
    GPIO.output(p, GPIO.LOW)

# ─── 4) Instantiate sensors (with built-in supervisor)
baud = cfg['serial']['baud']
sensors = {
    'temp': OneWireTemps(),
    'o2':   SensorSupervisor(SerialGas,
              max_failures=3,
              port  = cfg['serial']['o2_port'],
              cmd   = cfg['serial']['o2_cmd'],
              scale = cfg['serial']['o2_scale'],
              baud  = baud),
    'co2':  SensorSupervisor(SerialGas,
              max_failures=3,
              port  = cfg['serial']['co2_port'],
              cmd   = cfg['serial']['co2_cmd'],
              scale = cfg['serial']['co2_scale'],
              baud  = baud)
}

# ─── 5) Instantiate controllers
controllers = {
    'heater': HeaterController(
        cfg['gpio']['heaters'],
        cfg['setpoints']['temperature'],
        cfg['thresholds']['temperature'],
        cfg['pid']['heater']
    ),
    'o2': GasController(
        cfg['gpio']['o2_pin'],
        cfg['setpoints']['o2'],
        cfg['thresholds']['o2'],
        invert=True
    ),
    'co2': GasController(
        cfg['gpio']['co2_pin'],
        cfg['setpoints']['co2'],
        cfg['thresholds']['co2'],
        invert=False
    )
}

# ─── 6) Instantiate 7-segment displays (supervisor)
i2c = busio.I2C(board.SCL, board.SDA)
displays = {
    'o2':   DisplaySupervisor(i2c, cfg['i2c']['disp_o2']),
    'co2':  DisplaySupervisor(i2c, cfg['i2c']['disp_co2']),
    'temp': DisplaySupervisor(i2c, cfg['i2c']['disp_temp'])
}

# ─── 7) Graceful shutdown
def shutdown(signum, frame):
    logger.info(f"Signal {signum} received, shutting down")
    for p in all_pins:
        GPIO.output(p, GPIO.LOW)
    sys.exit(0)

signal.signal(signal.SIGINT,  shutdown)
signal.signal(signal.SIGTERM, shutdown)

# ─── 8) Run UI in a restart loop
while True:
    try:
        curses.wrapper(
            curses_main,
            sensors,
            controllers,
            displays,
            cfg['max_values']['o2'],
            cfg['max_values']['co2'],
            cfg['max_values']['temperature'],
            cfg['read_interval']
        )
        break
    except Exception:
        logger.exception("UI crashed, restarting in 5s")
        for p in all_pins:
            GPIO.output(p, GPIO.LOW)
        time.sleep(5)

# ─── 9) Final cleanup
for p in all_pins:
    GPIO.output(p, GPIO.LOW)
sys.exit(0)
