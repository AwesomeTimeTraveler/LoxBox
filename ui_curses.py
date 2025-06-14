# ui_curses.py

import time, curses, logging

logger = logging.getLogger("incubator.ui")

def curses_main(stdscr,
                sensors,
                controllers,
                displays,
                o2_max, co2_max, temp_max,
                read_interval):
    # 1) init
    curses.curs_set(0)
    stdscr.nodelay(True)
    curses.start_color()
    curses.use_default_colors()

    # gas & heater color pairs must match controllers.py
    curses.init_pair(1, curses.COLOR_GREEN,   -1)  # O₂ off
    curses.init_pair(5, curses.COLOR_YELLOW,  -1)  # O₂ pulse
    curses.init_pair(6, curses.COLOR_MAGENTA, -1)  # O₂ cont

    curses.init_pair(2, curses.COLOR_CYAN,    -1)  # CO₂ cont
    curses.init_pair(7, curses.COLOR_BLUE,    -1)  # CO₂ pulse
    curses.init_pair(8, curses.COLOR_RED,     -1)  # CO₂ off

    curses.init_pair(3, curses.COLOR_WHITE,   -1)  # Heater off
    curses.init_pair(9, curses.COLOR_GREEN,   -1)  # Heater pulse
    curses.init_pair(10, curses.COLOR_RED,    -1)  # Heater cont

    curses.init_pair(4, curses.COLOR_WHITE,   -1)  # labels/ticks

    max_y, max_x = stdscr.getmaxyx()
    usable = max_x - 20
    half_w = max(usable // 2, 10)
    start = time.time()

    # precompute tick labels
    o2_ticks  = [0, o2_max/4,  o2_max/2,  3*o2_max/4,  o2_max]
    lbl_o2    = [f"{x:.0f}%" for x in o2_ticks]

    co2_ticks = [0, co2_max/4, co2_max/2, 3*co2_max/4, co2_max]
    lbl_co2   = [f"{x:.0f}%" for x in co2_ticks]

    tmp_ticks = [0, temp_max/4, temp_max/2, 3*temp_max/4, temp_max]
    lbl_tmp   = [f"{x:.0f}" for x in tmp_ticks]

    while True:
        # 2) read
        now = time.time() - start
        t   = sensors['temp'].read()
        o   = sensors['o2'].read()
        c   = sensors['co2'].read()

        # 3) control
        controllers['heater'].update(t, now)
        controllers['o2'].update(o, now)
        controllers['co2'].update(c, now)

        # 4) draw
        stdscr.erase()

        # ─── O₂ bar row 1
        stdscr.addstr(1,1, f"O₂: {o:5.2f}%", curses.color_pair(4))
        wo = min(int(o / o2_max * half_w), half_w)
        stdscr.addnstr(1, 12, "█"*wo, half_w,
                       controllers['o2'].color(o))
        for i, lbl in enumerate(lbl_o2):
            x = 12 + int(i*(half_w/4))
            if x < max_x: stdscr.addstr(2, x, lbl, curses.color_pair(4))

        # ─── CO₂ bar row 1 (right side)
        offset = 12 + half_w + 5
        stdscr.addstr(1, offset, f"CO₂: {c:5.2f}%", curses.color_pair(4))
        wc = min(int(c / co2_max * half_w), half_w)
        stdscr.addnstr(1, offset+7, "█"*wc, half_w,
                       controllers['co2'].color(c))
        for i, lbl in enumerate(lbl_co2):
            x = offset+7 + int(i*(half_w/4))
            if x < max_x: stdscr.addstr(2, x, lbl, curses.color_pair(4))

        # ─── Temp bar row 4
        stdscr.addstr(4,1, f"T: {t:5.2f}°C", curses.color_pair(4))
        wt = min(int(t / temp_max * half_w), half_w)
        stdscr.addnstr(4, 12, "█"*wt, half_w,
                       controllers['heater'].color(t))
        for i, lbl in enumerate(lbl_tmp):
            x = 12 + int(i*(half_w/4))
            if x < max_x: stdscr.addstr(5, x, lbl, curses.color_pair(4))

        # ─── 7-segment safe updates
        for key, disp in displays.items():
            if not disp:
                continue
            val = {'o2': o, 'co2': c, 'temp': t}[key]
            try:
                disp.safe_print(f"{val:05.2f}")
            except Exception:
                displays[key] = None

        stdscr.addstr(max_y-2, 1, "Press 'q' to quit.", curses.color_pair(4))
        stdscr.refresh()

        # 5) exit or wait
        if stdscr.getch() == ord('q'):
            break
        time.sleep(read_interval)
