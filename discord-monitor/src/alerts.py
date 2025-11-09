from __future__ import annotations
from .models import IncubatorStatus
from typing import List, Optional

class Thresholds:
    def __init__(self, t_min: Optional[float], t_max: Optional[float], co2_max: Optional[float], o2_min: Optional[float]):
        self.t_min = t_min
        self.t_max = t_max
        self.co2_max = co2_max
        self.o2_min = o2_min

    def check(self, s: IncubatorStatus) -> List[str]:
        msgs: List[str] = []
        if self.t_min is not None and s.temp_c < self.t_min:
            msgs.append(f"Temp LOW: {s.temp_c:.2f}°C < {self.t_min:.2f}°C")
        if self.t_max is not None and s.temp_c > self.t_max:
            msgs.append(f"Temp HIGH: {s.temp_c:.2f}°C > {self.t_max:.2f}°C")
        if self.co2_max is not None and s.co2_pct is not None and s.co2_pct > self.co2_max:
            msgs.append(f"CO₂ HIGH: {s.co2_pct:.2f}% > {self.co2_max:.2f}%")
        if self.o2_min is not None and s.o2_pct is not None and s.o2_pct < self.o2_min:
            msgs.append(f"O₂ LOW: {s.o2_pct:.2f}% < {self.o2_min:.2f}%")
        return msgs