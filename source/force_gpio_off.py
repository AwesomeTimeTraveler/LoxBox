#!/usr/bin/env python3
"""
force_gpio_off.py
Ensures all incubator GPIO outputs are set LOW.

Use this as a last-resort shutdown hook (systemd ExecStopPost).
"""

import RPi.GPIO as GPIO
import yaml
import os
import sys

# Path to your config.yaml (adjust if needed)
CONFIG_PATH = "/home/brennan/incubator/config.yaml"

def main():
    try:
        if not os.path.exists(CONFIG_PATH):
            print(f"Config not found: {CONFIG_PATH}", file=sys.stderr)
            return 1

        # Load config to know which pins are used
        with open(CONFIG_PATH) as f:
            cfg = yaml.safe_load(f)

        all_pins = cfg['gpio']['heaters'] + [cfg['gpio']['o2_pin'], cfg['gpio']['co2_pin']]

        GPIO.setmode(GPIO.BCM)
        for p in all_pins:
            try:
                GPIO.setup(p, GPIO.OUT)
                GPIO.output(p, GPIO.LOW)
            except Exception as e:
                print(f"Error setting pin {p} LOW: {e}", file=sys.stderr)

        GPIO.cleanup()
        print("All incubator GPIO pins forced LOW.")
        return 0

    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
