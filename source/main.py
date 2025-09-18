#!/usr/bin/env python3
# main.py
print("DEBUG: entered main.py")
import os
import sys
import signal
import time
import curses
import yaml
import logging
import traceback
from logging.handlers import RotatingFileHandler
import RPi.GPIO as GPIO

import board, busio

from sensors import OneWireTemps, SerialGas, SensorSupervisor
from controllers import HeaterController, GasController
from display import DisplaySupervisor
from ui_curses import curses_main

# 1) Load configuration
with open("/home/brennan/incubator/v6/config.yaml") as f:
    cfg = yaml.safe_load(f)

# 2) Setup rotating logger
from logging.handlers import TimedRotatingFileHandler
import datetime

# 2) Setup logging — text + CSV
log_dir = cfg.get('log_dir', "/home/brennan/incubator/logs")
os.makedirs(log_dir, exist_ok=True)

# --- Human-readable log (daily rotation)
text_handler = TimedRotatingFileHandler(
    filename=os.path.join(log_dir, "incubator.log"),
    when="midnight", interval=1, backupCount=14, utc=False
)
text_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s'
))
logger = logging.getLogger("incubator")
logger.setLevel(logging.INFO)
logger.addHandler(text_handler)

# --- CSV data log (daily rotation)
csv_handler = TimedRotatingFileHandler(
    filename=os.path.join(log_dir, "incubator_data.csv"),
    when="midnight", interval=1, backupCount=14, utc=False
)
csv_handler.setFormatter(logging.Formatter('%(asctime)s,%(message)s'))
data_logger = logging.getLogger("incubator.data")
data_logger.setLevel(logging.INFO)
data_logger.addHandler(csv_handler)

# Write CSV header once per new file
if not os.path.exists(os.path.join(log_dir, "incubator_data.csv")):
    with open(os.path.join(log_dir, "incubator_data.csv"), "a") as f:
        f.write("timestamp,temp_c,o2_pct,co2_pct,heater_duty,o2_state,co2_state\n")

# 3) GPIO base mode & ensure everything off
GPIO.setmode(GPIO.BCM)
all_pins = cfg['gpio']['heaters'] + [cfg['gpio']['o2_pin'], cfg['gpio']['co2_pin']]
for p in all_pins:
    GPIO.setup(p, GPIO.OUT)
    GPIO.output(p, GPIO.LOW)

# 4) Instantiate sensors with supervisors
baud = cfg['serial']['baud']
sensors = {
    'temp': OneWireTemps(),
    'o2': SensorSupervisor(
        SerialGas,
        max_failures=3,
        port  = cfg['serial']['o2_port'],
        cmd   = cfg['serial']['o2_cmd'],
        scale = cfg['serial']['o2_scale'],
        baud  = baud
    ),
    'co2': SensorSupervisor(
        SerialGas,
        max_failures=3,
        port  = cfg['serial']['co2_port'],
        cmd   = cfg['serial']['co2_cmd'],
        scale = cfg['serial']['co2_scale'],
        baud  = baud
    )
}

#import pprint
#pprint.pprint(cfg['thresholds']['o2'])
#pprint.pprint(cfg['thresholds']['co2'])

# 5) Instantiate controllers
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

# 6) Instantiate and wrap the I²C displays
i2c = busio.I2C(board.SCL, board.SDA)
displays = {
    'o2':   DisplaySupervisor(i2c, cfg['i2c']['disp_o2']),
    'co2':  DisplaySupervisor(i2c, cfg['i2c']['disp_co2']),
    'temp': DisplaySupervisor(i2c, cfg['i2c']['disp_temp'])
}

# 7) Graceful shutdown
def shutdown(signum, frame):
    logger.info("Signal %d received, shutting down", signum)
    for p in all_pins:
        GPIO.output(p, GPIO.LOW)
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

# 8) Run the UI in a self-healing loop
print("DEBUG: about to start UI loop")
while True:
    try:
        curses.wrapper(
            curses_main,
            sensors,
            controllers,
            displays,
            cfg
            #cfg['max_values']['o2'],
            #cfg['max_values']['co2'],
            #cfg['max_values']['temperature'],
            #cfg['read_interval']
        )
        break
    except Exception:
        logger.exception("UI crashed; restarting in 5s")
        for p in all_pins:
            GPIO.output(p, GPIO.LOW)
        time.sleep(5)

# 9) Final cleanup
for p in all_pins:
    GPIO.output(p, GPIO.LOW)
sys.exit(0)
