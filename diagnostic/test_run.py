#!/usr/bin/env python3
import time, curses
from controllers import HeaterController, GasController
from ui_curses import curses_main
from display import DisplaySupervisor
from sim_sensors import SimOneWireTemps, SimGas, SimSupervisor

def main_test(stdscr):
    # set up a one‐second read interval
    read_interval = 1.0

    # Simulated sensors that ramp temperature from 20→37 over 10s,
    # O₂ from 20→2 over 30s, CO₂ from 0→5 over 20s
    sensors = {
        'temp': SimOneWireTemps(profile=[(0,20),(5,30),(10,37)]),
        'o2':   SimSupervisor(SimGas, profile=[(0,20),(15,10),(30,2)]),
        'co2':  SimSupervisor(SimGas, profile=[(0,0),(10,3),(20,5)])
    }

    # real controllers, with thresholds matching your config.yaml
    controllers = {
        'heater': HeaterController(pins=[5,6,13,19,26,27],
                                   setpt=37, thresh=0.98,
                                   pid_cfg={'Kp':1,'Ki':0.1,'Kd':0.01}),
        'o2':     GasController(pin=20, setpt=2.0,
                                thresholds={'continuous':0.75,'pulse':0.9,'off':1.1},
                                invert=True),
        'co2':    GasController(pin=21, setpt=5.0,
                                thresholds={'continuous':0.75,'pulse':0.9,'off':1.1},
                                invert=False)
    }

    # displays can be no‐ops or real if you have I2C loopback
    displays = {'o2':None,'co2':None,'temp':None}

    curses_main(
        stdscr,
        sensors,
        controllers,
        displays,
        o2_max=25, co2_max=20, temp_max=50,
        read_interval=read_interval
    )

if __name__=="__main__":
    curses.wrapper(main_test)
