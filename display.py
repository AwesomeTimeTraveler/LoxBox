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
            self.show()                # <-- push to hardware!
        except Exception:
            logger.exception("7-segment print/show failed")
            raise

def make_displays(i2c_addresses):
    """
    i2c_addresses: dict with keys 'o2', 'co2', 'temp'
                   and values the respective I2C addresses.
    Returns a dict of same keys mapping to SafeDisplay or None.
    """
    i2c = busio.I2C(board.SCL, board.SDA)
    out = {}
    for name, addr in i2c_addresses.items():
        try:
            disp = SafeDisplay(i2c, addr)
            disp.brightness = 1
            out[name] = disp
        except Exception:
            logger.exception(f"Failed to init {name} display @{hex(addr)}")
            out[name] = None
    return out
