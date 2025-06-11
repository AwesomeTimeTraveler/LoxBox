# display.py

import busio, board, logging
from adafruit_ht16k33 import segments

logger = logging.getLogger("incubator.display")

class SafeDisplay(segments.Seg7x4):
    def __init__(self, i2c, address):
        super().__init__(i2c, address)

    def safe_print(self, s):
        try:
            self.print(s)
        except Exception:
            logger.exception("7-seg print failed")
            raise

def make_displays():
    i2c = busio.I2C(board.SCL, board.SDA)
    out = {}
    for key, addr in [('o2', cfg['i2c']['disp_o2']),
                      ('co2',cfg['i2c']['disp_co2']),
                      ('temp',cfg['i2c']['disp_temp'])]:
        try:
            disp = SafeDisplay(i2c, addr)
            disp.brightness = 1
            out[key] = disp
        except Exception:
            out[key] = None
    return out
