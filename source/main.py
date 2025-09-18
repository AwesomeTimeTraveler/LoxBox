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
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import RPi.GPIO as GPIO

import board, busio

from sensors import OneWireTemps, SerialGas, SensorSupervisor
from controllers import HeaterController, GasController
from display import DisplaySupervisor
from ui_curses import curses_main

# 1) Load configuration
with open("/home/brennan/incubator/config.yaml") as f:
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
# --- CSV data log (daily rotation), alongside your text log ---
import os
log_dir = os.path.dirname(cfg['log_file']) or "."
os.makedirs(log_dir, exist_ok=True)
csv_path = os.path.join(log_dir, "incubator_data.csv")

csv_handler = TimedRotatingFileHandler(
    csv_path, when="midnight", interval=1, backupCount=14
)
csv_handler.setFormatter(logging.Formatter('%(asctime)s,%(message)s'))
data_logger = logging.getLogger("incubator.data")
data_logger.setLevel(logging.INFO)
data_logger.addHandler(csv_handler)

# Ensure header on first write / after rotation
try:
    if not os.path.exists(csv_path) or os.stat(csv_path).st_size == 0:
        with open(csv_path, "a") as f:
            f.write("timestamp,temp_c,o2_pct,co2_pct,heater_state,o2_state,co2_state\n")
except Exception:
    logger.exception("Failed to ensure CSV header")



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
        invert=False,
        pulse_on_s=0.10,          # 100 ms micro-pulse
        settle_s=6.0,             # 6 s wait before next pulse
        startup_soft_secs=120,    # first 2 min = conservative
        startup_pulse_on_s=0.06,  # 60 ms pulse at startup
        startup_settle_s=8.0,     # 8 s wait at startup
        rise_suppression=0.20     # stop dosing if rising >0.2 %/s
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
