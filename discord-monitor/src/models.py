from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class IncubatorStatus(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    # Core signals (humidity/fan removed)
    temp_c: float
    co2_pct: Optional[float] = None
    o2_pct: Optional[float] = None
    # Arbitrary on/off states from controller
    states: Dict[str, bool] = {}
    # Extra passthrough
    extra: Dict[str, Any] = {}

    def as_lines(self, units: str = "C") -> list[str]:
        t = self.temp_c if units == "C" else (self.temp_c * 9/5 + 32)
        t_unit = "°C" if units == "C" else "°F"
        lines = [f"Temp: {t:.2f}{t_unit}"]
        if self.co2_pct is not None:
            lines.append(f"CO₂: {self.co2_pct:.2f}%")
        if self.o2_pct is not None:
            lines.append(f"O₂: {self.o2_pct:.2f}%")
        if self.states:
            pretty = ", ".join(f"{k}:{'ON' if v else 'off'}" for k,v in self.states.items())
            lines.append(f"States: {pretty}")
        return lines