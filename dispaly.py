# display.py

import logging
from adafruit_ht16k33 import segments

logger = logging.getLogger("incubator.display")

class DisplaySupervisor(segments.Seg7x4):
    """
    A 7‐segment display wrapper that
    catches I2C errors on print/show.
    """
    def __init__(self, i2c, address):
        super().__init__(i2c, address)

    def safe_print(self, s):
        try:
            self.print(s)
            self.show()
        except Exception:
            logger.exception(f"Display @0x{self.address:x} failed")
            # disable further use by re-raising
            raise
