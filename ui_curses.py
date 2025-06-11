# ui_curses.py

import curses, time, logging

logger = logging.getLogger("incubator.ui")

def curses_main(stdscr, sensors, controllers, displays, cfg):
    # Basic curses setup
    curses.curs_set(0)
    stdscr.nodelay(True)
    curses.start_color()
    curses.use_default_colors()

    # Init color pairs
    curses.init_pair(1, curses.COLOR_GREEN,   -1)
    curses.init_pair(2, curses.COLOR_CYAN,    -1)
    curses.init_pair(3, curses.COLOR_WHITE,   -1)
    curses.init_pair(4, curses.COLOR_WHITE,   -1)  # labels
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
    o2_max   = cfg['max_values']['o2']
    co2_max  = cfg['max_values']['co2']
    tmp_max  = cfg['max_values']['temperature']

    o2_ticks = [0, o2_max/4, o2_max/2, 3*o2_max/4, o2_max]
    o2_lbl   = [f"{t:.0f}%" for t in o2_ticks]

    co2_ticks = [0, co2_max/4, co2_max/2, 3*co2_max/4, co2_max]
    co2_lbl   = [f"{t:.0f}%" for t in co2_ticks]

    tmp_ticks = [0, tmp_max/4, tmp_max/2, 3*tmp_max/4, tmp_max]
    tmp_lbl   = [f"{t:.0f}" for t in tmp_ticks]

    while True:
        now = time.time() - start

        # 1) Read sensors
        t = sensors['temp'].read()
        o = sensors['o2'].read()
        c = sensors['co2'].read()

        # 2) Log metrics
        logger.info("T:%.2f O2:%.2f CO2:%.2f", t, o, c)

        # 3) Update controllers
        controllers['heater'].update(t, now)
        controllers['o2'].update(o, now)
        controllers['co2'].update(c, now)

        # 4) Draw UI
        stdscr.erase()

        # O₂ bar
        stdscr.addstr(1,1, f"O₂: {o:5.2f}%", curses.color_pair(4))
        w_o = min(int(o/o2_max * half_w), half_w)
        stdscr.addnstr(1,12, "█"*w_o, half_w, controllers['o2'].color(o))
        for i, lbl in enumerate(o2_lbl):
            x = 12 + int(i*(half_w/4))
            if x<max_x: stdscr.addstr(2, x, lbl, curses.color_pair(4))

        # CO₂ bar
        off = 12 + half_w + 5
        stdscr.addstr(1,off, f"CO₂: {c:5.2f}%", curses.color_pair(4))
        w_c = min(int(c/co2_max * half_w), half_w)
        stdscr.addnstr(1, off+7, "█"*w_c, half_w, controllers['co2'].color(c))
        for i, lbl in enumerate(co2_lbl):
            x = off+7 + int(i*(half_w/4))
            if x<max_x: stdscr.addstr(2, x, lbl, curses.color_pair(4))

        # Temp bar
        stdscr.addstr(4,1, f"T: {t:5.2f}°C", curses.color_pair(4))
        w_t = min(int(t/tmp_max * half_w), half_w)
        stdscr.addnstr(4,12, "█"*w_t, half_w, controllers['heater'].color(t))
        for i, lbl in enumerate(tmp_lbl):
            x = 12 + int(i*(half_w/4))
            if x<max_x: stdscr.addstr(5, x, lbl, curses.color_pair(4))

        # 7-seg displays
        for key in ('o2','co2','temp'):
            disp = displays.get(key)
            val  = {'o2':o,'co2':c,'temp':t}[key]
            if disp:
                try:
                    disp.safe_print(f"{val:05.2f}")
                except Exception:
                    displays[key]=None

        stdscr.addstr(max_y-2,1, "Press 'q' to quit.", curses.color_pair(4))
        stdscr.refresh()

        if stdscr.getch()==ord('q'): break
        time.sleep(cfg['read_interval'])
