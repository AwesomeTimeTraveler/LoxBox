#!/usr/bin/env python3
import os, sys, signal, time, curses, yaml, logging, traceback
from logging.handlers import RotatingFileHandler
import RPi.GPIO as GPIO

from sensors import OneWireTemps, SerialGas
from controllers import HeaterController, GasController
from display import make_displays
from ui_curses import curses_main

# 1) Load config
with open("/home/brennan/Desktop/incubator/final/v3/config.yaml") as f:
    cfg = yaml.safe_load(f)

# 
# Handler - for logging X number of days
# Set to 365 days @ midnight
#

from logging.handlers import TimedRotatingFileHandler

handler = TimedRotatingFileHandler(
    cfg['log_file'],
    when="midnight",
    interval=1,
    backupCount=365
)
handler.suffix = "%Y-%m-%d"  # filenames like incubator.log.2025-06-10


logger = logging.getLogger("incubator")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# 3) Setup GPIO to BCM numbering
GPIO.setmode(GPIO.BCM)

# 4) Instantiate modules
sensors = {
    'temp': OneWireTemps(),
    'o2':   SerialGas(cfg['serial']['o2_port'], cfg['serial']['o2_cmd'], cfg['serial']['o2_scale'], cfg['serial']['baud']),
    'co2':  SerialGas(cfg['serial']['co2_port'], cfg['serial']['co2_cmd'], cfg['serial']['co2_scale'], cfg['serial']['baud'])
}

controllers = {
    'heater': HeaterController(cfg['gpio']['heaters'], cfg['setpoints']['temperature'], cfg['thresholds']['temperature'], cfg['pid']['heater']),
    'o2':     GasController(cfg['gpio']['o2_pin'], cfg['setpoints']['o2'], cfg['thresholds']['o2'], invert=True),
    'co2':    GasController(cfg['gpio']['co2_pin'], cfg['setpoints']['co2'], cfg['thresholds']['co2'], invert=False)
}

displays = make_displays()

# 5) Graceful shutdown - don't melt the box or make a bomb
def shutdown(signum, frame):
    logger.info("Signal %d received, shutting down", signum)
    for pin in (cfg['gpio']['o2_pin'], cfg['gpio']['co2_pin']) + tuple(cfg['gpio']['heaters']):
        GPIO.output(pin, GPIO.LOW)
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

# 6) Main loop
while True:
    try:
        curses.wrapper(curses_main, sensors, controllers, displays, cfg)
        break
    except Exception:
        logger.exception("UI crashed; restarting in 5s")
        for pin in (cfg['gpio']['o2_pin'], cfg['gpio']['co2_pin']) + tuple(cfg['gpio']['heaters']):
            GPIO.output(pin, GPIO.LOW)
        time.sleep(5)

# final cleanup
for pin in (cfg['gpio']['o2_pin'], cfg['gpio']['co2_pin']) + tuple(cfg['gpio']['heaters']):
    GPIO.output(pin, GPIO.LOW)
sys.exit(0)
