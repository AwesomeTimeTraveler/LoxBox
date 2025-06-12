#!/usr/bin/env python3
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

from sensors import OneWireTemps, SerialGas
from controllers import HeaterController, GasController
from display import make_displays
from ui_curses import curses_main

# ─── 1) Load configuration ──────────────────────────────────────────────────────
with open("/home/brennan/incubator/config.yaml") as f:
    cfg = yaml.safe_load(f)

# ─── 2) Setup rotating logger ──────────────────────────────────────────────────
handler = RotatingFileHandler(
    cfg['log_file'], maxBytes=1_000_000, backupCount=5
)
handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s'
))
logger = logging.getLogger("incubator")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# ─── 3) GPIO base mode ──────────────────────────────────────────────────────────
GPIO.setmode(GPIO.BCM)

all_pins = [cfg['gpio']['o2_pin'], cfg['gpio']['co2_pin']] + cfg['gpio']['heaters']
for pin in all_pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# ─── 4) Instantiate sensors ─────────────────────────────────────────────────────
baud = cfg['serial']['baud']
sensors = {
    'temp': OneWireTemps(),
    'o2':   SerialGas(
        cfg['serial']['o2_port'],
        cfg['serial']['o2_cmd'],
        cfg['serial']['o2_scale'],
        baud
    ),
    'co2':  SerialGas(
        cfg['serial']['co2_port'],
        cfg['serial']['co2_cmd'],
        cfg['serial']['co2_scale'],
        baud
    )
}

# ─── 5) Instantiate controllers ─────────────────────────────────────────────────
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
        cfg['gas_thresholds']['o2'],    # ← now passes a dict
        invert=True
    ),
    'co2': GasController(
        cfg['gpio']['co2_pin'],
        cfg['setpoints']['co2'],
        cfg['gas_thresholds']['co2'],   # ← now passes a dict
        invert=False
    )
}


# ─── 6) Instantiate 7-segment displays ──────────────────────────────────────────
displays = make_displays({
    'o2':   cfg['i2c']['disp_o2'], #0x70
    'co2':  cfg['i2c']['disp_co2'], #0x71
    'temp': cfg['i2c']['disp_temp'] #0x72
})

# ─── 7) Graceful shutdown handler ───────────────────────────────────────────────
def shutdown(signum, frame):
    logger.info("Signal %d received, shutting down", signum)
    # turn everything off
    all_pins = controllers['heater'].pins + [
        cfg['gpio']['o2_pin'], cfg['gpio']['co2_pin']
    ]
    for pin in all_pins:
        GPIO.output(pin, GPIO.LOW)
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

# ─── 8) Run the curses UI in a restart loop ────────────────────────────────────
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
        logger.exception("UI crashed; restarting in 5s")
        # ensure relays off before retry
        all_pins = controllers['heater'].pins + [
            cfg['gpio']['o2_pin'], cfg['gpio']['co2_pin']
        ]
        for pin in all_pins:
            GPIO.output(pin, GPIO.LOW)
        time.sleep(5)

# ─── 9) Final cleanup ──────────────────────────────────────────────────────────
all_pins = controllers['heater'].pins + [
    cfg['gpio']['o2_pin'], cfg['gpio']['co2_pin']
]
for pin in all_pins:
    GPIO.output(pin, GPIO.LOW)

sys.exit(0)
