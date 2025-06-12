# ui_curses.py

import curses
import time
import logging

logger = logging.getLogger("incubator.ui")

def curses_main(
    stdscr,
    sensors,
    controllers,
    displays,
    o2_max,
    co2_max,
    temp_max,
    read_interval
):
    # 1) Curses initialization
    curses.curs_set(0)
    stdscr.nodelay(True)
    curses.start_color()
    curses.use_default_colors()
    # Color pairs (1–10)
    curses.init_pair(1, curses.COLOR_GREEN,   -1)
    curses.init_pair(2, curses.COLOR_CYAN,    -1)
    curses.init_pair(3, curses.COLOR_WHITE,   -1)
    curses.init_pair(4, curses.COLOR_WHITE,   -1)  # labels/ticks
    curses.init_pair(5, curses.COLOR_YELLOW,  -1)
    curses.init_pair(6, curses.COLOR_MAGENTA, -1)
    curses.init_pair(7, curses.COLOR_BLUE,    -1)
    curses.init_pair(8, curses.COLOR_RED,     -1)
    curses.init_pair(9, curses.COLOR_GREEN,   -1)
    curses.init_pair(10, curses.COLOR_RED,    -1)

    max_y, max_x = stdscr.getmaxyx()
    usable = max_x - 20
    half_w = max(usable // 2, 10)
    start = time.time()

    # Precompute tick labels
    o2_lbl  = [f"{i*o2_max/4:.0f}%" for i in range(5)]
    co2_lbl = [f"{i*co2_max/4:.0f}%" for i in range(5)]
    tmp_lbl = [f"{i*temp_max/4:.0f}"  for i in range(5)]

    while True:
        now = time.time() - start

        # 2) Read sensors
        t = sensors['temp'].read()
        o = sensors['o2'].read()
        c = sensors['co2'].read()

        # 3) Log
        logger.info("T:%.2f O2:%.2f CO2:%.2f", t, o, c)

        # 4) Update controllers
        controllers['heater'].update(t, now)
        controllers['o2'].update(o, now)
        controllers['co2'].update(c, now)

        # 5) Draw UI
        stdscr.erase()

        # O₂ bar + ticks
        stdscr.addstr(1, 1, f"O₂: {o:5.2f}%", curses.color_pair(4))
        w_o = min(int(o/o2_max * half_w), half_w)
        stdscr.addnstr(1, 12, "█"*w_o, half_w, controllers['o2'].color(o))
        for i, lbl in enumerate(o2_lbl):
            x = 12 + int(i*(half_w/4))
            if x < max_x:
                stdscr.addstr(2, x, lbl, curses.color_pair(4))

        # CO₂ bar + ticks
        off = 12 + half_w + 5
        stdscr.addstr(1, off, f"CO₂: {c:5.2f}%", curses.color_pair(4))
        w_c = min(int(c/co2_max * half_w), half_w)
        stdscr.addnstr(1, off+7, "█"*w_c, half_w, controllers['co2'].color(c))
        for i, lbl in enumerate(co2_lbl):
            x = off+7 + int(i*(half_w/4))
            if x < max_x:
                stdscr.addstr(2, x, lbl, curses.color_pair(4))

        # Temperature bar + ticks
        stdscr.addstr(4, 1, f"T: {t:5.2f}°C", curses.color_pair(4))
        w_t = min(int(t/temp_max * half_w), half_w)
        stdscr.addnstr(4, 12, "█"*w_t, half_w, controllers['heater'].color(t))
        for i, lbl in enumerate(tmp_lbl):
            x = 12 + int(i*(half_w/4))
            if x < max_x:
                stdscr.addstr(5, x, lbl, curses.color_pair(4))

        # 6) Update 7-segments safely
        for key in ('o2', 'co2', 'temp'):
            disp = displays.get(key)
            val  = {'o2': o, 'co2': c, 'temp': t}[key]
            if disp:
                try:
                    disp.safe_print(f"{val:05.2f}")
                except Exception:
                    displays[key] = None

        stdscr.addstr(max_y-2, 1, "Press 'q' to quit.", curses.color_pair(4))
        stdscr.refresh()

        # 7) Exit on 'q'
        if stdscr.getch() == ord('q'):
            break

        time.sleep(read_interval)
